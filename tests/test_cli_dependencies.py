from pathlib import Path

from pyauditor.cli.bootstrap import check_bootstrap_ready
from pyauditor.cli.consolidate import check_consolidate_ready
from pyauditor.cli.dependencies import CHECKERS
from pyauditor.cli.measure import check_measure_ready
from pyauditor.cli.report import check_report_ready
from pyauditor.excel.capa import COMMON_FIELD_LABELS, ORGAO_FIELD_LABELS, bootstrap_capa_csv


def test_registry_maps_every_command_to_its_checker() -> None:
    assert CHECKERS["bootstrap"] is check_bootstrap_ready
    assert CHECKERS["measure"] is check_measure_ready
    assert CHECKERS["report"] is check_report_ready
    assert CHECKERS["consolidate"] is check_consolidate_ready


def test_bootstrap_and_measure_have_no_dependencies() -> None:
    assert check_bootstrap_ready().satisfied
    assert check_measure_ready().satisfied


def test_report_ready_requires_comum_and_orgao_capas_and_roms(tmp_path: Path) -> None:
    comum = tmp_path / "capa.csv"
    roms_dir = tmp_path / "roms"

    check = check_report_ready("2026-06", "MinC", comum, roms_dir, data_dir=tmp_path)

    assert not check.satisfied
    assert len(check.missing) == 3  # capa comum + capa MinC + ROMs

    bootstrap_capa_csv(comum, COMMON_FIELD_LABELS)
    bootstrap_capa_csv(tmp_path / "capa_MinC.csv", ORGAO_FIELD_LABELS)
    (roms_dir / "2026-06").mkdir(parents=True)

    check = check_report_ready("2026-06", "MinC", comum, roms_dir, data_dir=tmp_path)
    assert check.satisfied
    assert check.missing == ()


def test_consolidate_ready_requires_both_orgao_reports_and_roms(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports"
    roms_dir = tmp_path / "roms"

    check = check_consolidate_ready("2026-06", report_dir, roms_dir)
    assert not check.satisfied
    assert len(check.missing) == 4  # 2 reports + 2 ROMs dirs

    report_dir.mkdir()
    (report_dir / "relatorio_2026-06_MinC.xlsx").touch()
    (report_dir / "relatorio_2026-06_MTur.xlsx").touch()
    (roms_dir / "MinC" / "2026-06").mkdir(parents=True)
    (roms_dir / "MTur" / "2026-06").mkdir(parents=True)

    check = check_consolidate_ready("2026-06", report_dir, roms_dir)
    assert check.satisfied
