import json
from pathlib import Path

from openpyxl import load_workbook

from pyauditor.cli.report import run_report
from pyauditor.excel.capa import FIELD_LABELS, SHEET_NAME, bootstrap_capa
from pyauditor.excel.report import GLOSAS_SHEET, INMS_BASE_SHEET


def _write_summary(roms_dir: Path, competencia: str, indicator_id: str, contractual_id: str) -> None:
    target_dir = roms_dir / competencia
    target_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "indicator_id": indicator_id,
        "contractual_id": contractual_id,
        "name": f"Indicador {contractual_id}",
        "asset": None,
        "orgao": "MinC",
        "shape": "ratio",
        "target_operator": ">=",
        "target_value": 98.0,
        "result_pct": 97.71,
        "conforms": False,
        "penalty_points": 222.14,
        "numerator": 171,
        "denominator": 175,
        "hard_failure": False,
    }
    (target_dir / f"{indicator_id}.json").write_text(json.dumps(summary), encoding="utf-8")
    (target_dir / f"{indicator_id}.md").write_text("# ROM", encoding="utf-8")


def _write_summary_with_points(
    roms_dir: Path, competencia: str, indicator_id: str, contractual_id: str, penalty_points: float
) -> None:
    target_dir = roms_dir / competencia
    target_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "indicator_id": indicator_id,
        "contractual_id": contractual_id,
        "name": f"Indicador {contractual_id}",
        "asset": None,
        "orgao": "MinC",
        "shape": "ratio",
        "target_operator": ">=",
        "target_value": 98.0,
        "result_pct": 97.71,
        "conforms": False,
        "penalty_points": penalty_points,
        "numerator": 171,
        "denominator": 175,
        "hard_failure": False,
    }
    (target_dir / f"{indicator_id}.json").write_text(json.dumps(summary), encoding="utf-8")
    (target_dir / f"{indicator_id}.md").write_text("# ROM", encoding="utf-8")


def test_run_report_persists_glosa_historico(tmp_path: Path) -> None:
    capa_path = tmp_path / "capa.xlsx"
    bootstrap_capa(capa_path)
    roms_dir = tmp_path / "roms"
    # 40000 pontos -> 40% bruto, capped 30%, 10 p.p. de saldo rolado
    _write_summary_with_points(roms_dir, "2026-06", "INMS-1.1", "INMS 1.1", 40_000.0)
    output_path = tmp_path / "reports" / "relatorio_2026-06.xlsx"

    exit_code = run_report("2026-06", capa_path, roms_dir, output_path, config_dir=tmp_path / "configs")

    assert exit_code == 0
    historico = json.loads((roms_dir / "glosa_historico.json").read_text(encoding="utf-8"))
    assert historico["2026-06"]["saldo_rolado_pct"] == 10.0
    assert historico["2026-06"]["teto_atingido"] is True


def test_run_report_next_competencia_consumes_rollover(tmp_path: Path) -> None:
    capa_path = tmp_path / "capa.xlsx"
    bootstrap_capa(capa_path)
    roms_dir = tmp_path / "roms"
    _write_summary_with_points(roms_dir, "2026-06", "INMS-1.1", "INMS 1.1", 40_000.0)
    run_report(
        "2026-06", capa_path, roms_dir, tmp_path / "reports" / "relatorio_2026-06.xlsx",
        config_dir=tmp_path / "configs",
    )

    # Julho sem nenhuma penalidade nova — só o saldo rolado de junho (10 p.p.)
    _write_summary_with_points(roms_dir, "2026-07", "INMS-1.1", "INMS 1.1", 0.0)
    output_path = tmp_path / "reports" / "relatorio_2026-07.xlsx"
    exit_code = run_report("2026-07", capa_path, roms_dir, output_path, config_dir=tmp_path / "configs")

    assert exit_code == 0
    workbook = load_workbook(output_path)
    glosas_sheet = workbook[GLOSAS_SHEET]
    assert glosas_sheet.cell(row=2, column=3).value == 10.0  # saldo recebido do mês anterior
    assert glosas_sheet.cell(row=2, column=4).value == 10.0  # percentual de ajuste


def test_run_report_final_month_does_not_roll_over(tmp_path: Path) -> None:
    capa_path = tmp_path / "capa.xlsx"
    bootstrap_capa(capa_path)
    roms_dir = tmp_path / "roms"
    _write_summary_with_points(roms_dir, "2026-06", "INMS-1.1", "INMS 1.1", 40_000.0)
    output_path = tmp_path / "reports" / "relatorio_2026-06.xlsx"

    exit_code = run_report(
        "2026-06", capa_path, roms_dir, output_path, config_dir=tmp_path / "configs", is_final_month=True
    )

    assert exit_code == 0
    historico = json.loads((roms_dir / "glosa_historico.json").read_text(encoding="utf-8"))
    assert historico["2026-06"]["saldo_rolado_pct"] == 0.0


def test_run_report_fails_without_capa(tmp_path: Path) -> None:
    capa_path = tmp_path / "capa.xlsx"
    roms_dir = tmp_path / "roms"
    _write_summary(roms_dir, "2026-06", "INMS-1.1", "INMS 1.1")

    exit_code = run_report("2026-06", capa_path, roms_dir, tmp_path / "reports" / "out.xlsx", config_dir=tmp_path / "configs")

    assert exit_code == 1
    assert not (tmp_path / "reports" / "out.xlsx").exists()


def test_run_report_fails_without_roms(tmp_path: Path) -> None:
    capa_path = tmp_path / "capa.xlsx"
    bootstrap_capa(capa_path)
    roms_dir = tmp_path / "roms"  # never populated

    exit_code = run_report("2026-06", capa_path, roms_dir, tmp_path / "reports" / "out.xlsx", config_dir=tmp_path / "configs")

    assert exit_code == 1


def test_run_report_builds_workbook_from_summaries(tmp_path: Path) -> None:
    capa_path = tmp_path / "capa.xlsx"
    bootstrap_capa(capa_path)
    roms_dir = tmp_path / "roms"
    _write_summary(roms_dir, "2026-06", "INMS-1.1", "INMS 1.1")
    output_path = tmp_path / "reports" / "relatorio.xlsx"

    exit_code = run_report("2026-06", capa_path, roms_dir, output_path, config_dir=tmp_path / "configs")

    assert exit_code == 0
    assert output_path.exists()

    workbook = load_workbook(output_path)
    assert INMS_BASE_SHEET in workbook.sheetnames
    sheet = workbook[INMS_BASE_SHEET]
    assert sheet.cell(row=2, column=5).value == "INMS 1.1"


def test_run_report_is_regenerated_not_cumulative(tmp_path: Path) -> None:
    capa_path = tmp_path / "capa.xlsx"
    bootstrap_capa(capa_path)
    roms_dir = tmp_path / "roms"
    _write_summary(roms_dir, "2026-06", "INMS-1.1", "INMS 1.1")
    output_path = tmp_path / "reports" / "relatorio.xlsx"

    run_report("2026-06", capa_path, roms_dir, output_path, config_dir=tmp_path / "configs")
    first_size = output_path.stat().st_size

    # Second indicator appears for the same competência — rerun must reflect
    # exactly the current ROMs, not append to the previous run's workbook.
    _write_summary(roms_dir, "2026-06", "INMS-1.2", "INMS 1.2")
    run_report("2026-06", capa_path, roms_dir, output_path, config_dir=tmp_path / "configs")

    workbook = load_workbook(output_path)
    sheet = workbook[INMS_BASE_SHEET]
    codes = [str(sheet.cell(row=r, column=5).value) for r in range(2, sheet.max_row + 1)]
    assert sorted(codes) == ["INMS 1.1", "INMS 1.2"]
    assert output_path.stat().st_size != first_size or len(codes) == 2


def test_run_report_reads_valor_base_from_capa_for_glosas(tmp_path: Path) -> None:
    capa_path = tmp_path / "capa.xlsx"
    bootstrap_capa(capa_path)
    capa_workbook = load_workbook(capa_path)
    capa_sheet = capa_workbook[SHEET_NAME]
    row = 4 + FIELD_LABELS.index("Valor mensal vigente")
    capa_sheet.cell(row=row, column=2, value=100_000.0)
    capa_workbook.save(capa_path)

    roms_dir = tmp_path / "roms"
    _write_summary(roms_dir, "2026-06", "INMS-1.1", "INMS 1.1")  # penalty_points=222.14
    output_path = tmp_path / "reports" / "relatorio.xlsx"

    exit_code = run_report("2026-06", capa_path, roms_dir, output_path, config_dir=tmp_path / "configs")

    assert exit_code == 0
    workbook = load_workbook(output_path)
    glosas_sheet = workbook[GLOSAS_SHEET]
    assert glosas_sheet.cell(row=2, column=5).value == 100_000.0  # Valor-base
    assert glosas_sheet.cell(row=2, column=6).value == 222.14  # 0.22214% de 100.000
