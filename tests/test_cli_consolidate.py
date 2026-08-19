import json
from pathlib import Path

from openpyxl import load_workbook

from pyauditor.cli.consolidate import run_consolidate
from pyauditor.cli.report import run_report
from pyauditor.excel.capa import FIELD_LABELS, SHEET_NAME, bootstrap_capa
from pyauditor.excel.consolidate import GLOSAS_SHEET


def _write_summary(
    roms_dir: Path, competencia: str, orgao: str, indicator_id: str, contractual_id: str,
    *, penalty_points: float = 0.0, conforms: bool = True,
) -> None:
    target_dir = roms_dir / orgao / competencia
    target_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "indicator_id": indicator_id,
        "contractual_id": contractual_id,
        "name": f"Indicador {contractual_id}",
        "asset": None,
        "orgao": orgao,
        "shape": "ratio",
        "target_operator": ">=",
        "target_value": 98.0,
        "result_pct": 97.71,
        "conforms": conforms,
        "penalty_points": penalty_points,
        "numerator": 171,
        "denominator": 175,
        "hard_failure": False,
    }
    (target_dir / f"{indicator_id}.json").write_text(json.dumps(summary), encoding="utf-8")
    (target_dir / f"{indicator_id}.md").write_text("# ROM", encoding="utf-8")


def _build_orgao_report(tmp_path: Path, orgao: str, valor_mensal: float = 100_000.0) -> None:
    capa_path = tmp_path / f"capa_{orgao}.xlsx"
    bootstrap_capa(capa_path)
    workbook = load_workbook(capa_path)
    sheet = workbook[SHEET_NAME]
    row = 4 + FIELD_LABELS.index("Valor mensal vigente")
    sheet.cell(row=row, column=2, value=valor_mensal)
    workbook.save(capa_path)

    roms_dir = tmp_path / "roms"
    _write_summary(
        roms_dir, "2026-06", orgao, f"INMS-1.6-{orgao}", "INMS 1.6",
        penalty_points=100.0, conforms=False,
    )

    output_path = tmp_path / "reports" / f"relatorio_2026-06_{orgao}.xlsx"
    exit_code = run_report(
        "2026-06", capa_path, roms_dir / orgao, output_path,
        config_dir=tmp_path / "configs" / orgao,
    )
    assert exit_code == 0


def test_run_consolidate_fails_when_a_report_is_missing(tmp_path: Path) -> None:
    _build_orgao_report(tmp_path, "MinC")
    # MTur report never built.

    exit_code = run_consolidate(
        "2026-06", tmp_path / "reports", tmp_path / "roms",
        tmp_path / "reports" / "relatorio_2026-06_consolidado.xlsx",
    )

    assert exit_code == 1
    assert not (tmp_path / "reports" / "relatorio_2026-06_consolidado.xlsx").exists()


def test_run_consolidate_builds_workbook_from_both_orgaos(tmp_path: Path) -> None:
    _build_orgao_report(tmp_path, "MinC")
    _build_orgao_report(tmp_path, "MTur")
    output_path = tmp_path / "reports" / "relatorio_2026-06_consolidado.xlsx"

    exit_code = run_consolidate("2026-06", tmp_path / "reports", tmp_path / "roms", output_path)

    assert exit_code == 0
    assert output_path.exists()
    workbook = load_workbook(output_path)
    sheet = workbook[GLOSAS_SHEET]
    orgaos = {sheet.cell(row=r, column=2).value for r in (2, 3)}
    assert orgaos == {"MinC", "MTur"}


def test_run_consolidate_never_regenerates_the_orgao_reports(tmp_path: Path) -> None:
    _build_orgao_report(tmp_path, "MinC")
    _build_orgao_report(tmp_path, "MTur")
    report_path = tmp_path / "reports" / "relatorio_2026-06_MinC.xlsx"
    original_mtime = report_path.stat().st_mtime_ns

    run_consolidate(
        "2026-06", tmp_path / "reports", tmp_path / "roms",
        tmp_path / "reports" / "relatorio_2026-06_consolidado.xlsx",
    )

    assert report_path.stat().st_mtime_ns == original_mtime


def test_run_consolidate_rerun_preserves_fiscal_decision(tmp_path: Path) -> None:
    _build_orgao_report(tmp_path, "MinC")
    _build_orgao_report(tmp_path, "MTur")
    output_path = tmp_path / "reports" / "relatorio_2026-06_consolidado.xlsx"

    run_consolidate("2026-06", tmp_path / "reports", tmp_path / "roms", output_path)

    workbook = load_workbook(output_path)
    sheet = workbook[GLOSAS_SHEET]
    header = [cell.value for cell in sheet[1]]
    decisao_col = header.index("Decisão Fiscal") + 1
    sheet.cell(row=2, column=decisao_col, value="Aceita")
    workbook.save(output_path)

    run_consolidate("2026-06", tmp_path / "reports", tmp_path / "roms", output_path)

    reread = load_workbook(output_path)
    reread_sheet = reread[GLOSAS_SHEET]
    decisoes = {reread_sheet.cell(row=r, column=decisao_col).value for r in (2, 3)}
    assert "Aceita" in decisoes
