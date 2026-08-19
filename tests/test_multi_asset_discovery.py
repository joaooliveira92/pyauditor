"""Multi-asset file discovery: a per-asset indicator like INMS 1.14 has
several independent YAML+CSV measurements (one per named service — File
Server, WI-FI, etc.) sharing one `contractual_id`. `measure` must write each
to its own ROM/JSON (no collision), and `report` must show one row per asset
in `INMS_BASE` and the relevant group tab, not one deduplicated-to-the-
indicator row. Proven synthetically — no real multi-asset dataset exists yet
in /input (ticket 13).
"""

from pathlib import Path

import pytest

from pyauditor.cli.measure import run_measure
from pyauditor.engine.pipeline import discover_configs, measure
from pyauditor.excel.report import INMS_BASE_SHEET, build_report_workbook
from pyauditor.rom.render import render_rom
from pyauditor.rom.summary import summarize

REPO_ROOT = Path(__file__).parent.parent
CONFIG_DIR = REPO_ROOT / "tests" / "fixtures" / "multi_asset_configs"


def _write_csvs(data_dir: Path) -> None:
    competencia_data_dir = data_dir / "2026" / "06"
    competencia_data_dir.mkdir(parents=True, exist_ok=True)
    (competencia_data_dir / "inms-1.14-file-server.csv").write_text(
        "Descrição,Disponibilidade Realizada (%)\nFile Server,99.80\n", encoding="utf-8"
    )
    (competencia_data_dir / "inms-1.14-wifi.csv").write_text(
        "Descrição,Disponibilidade Realizada (%)\nWI-FI,98.90\n", encoding="utf-8"
    )


def _competencia_data_dir(data_dir: Path) -> Path:
    return data_dir / "2026" / "06"


def test_discover_configs_finds_both_assets() -> None:
    configs = discover_configs(CONFIG_DIR)

    assert len(configs) == 2
    contractual_ids = {c.indicator.contractual_id for c in configs}
    assert contractual_ids == {"INMS 1.14"}
    assets = {c.indicator.asset for c in configs}
    assert assets == {"File Server", "WI-FI"}
    ids = {c.indicator.id for c in configs}
    assert ids == {"INMS-1.14-FILE-SERVER", "INMS-1.14-WIFI"}


def test_measure_writes_distinct_rom_and_summary_per_asset(tmp_path: Path) -> None:
    _write_csvs(tmp_path)

    for config in discover_configs(CONFIG_DIR):
        result = measure(config, data_dir=_competencia_data_dir(tmp_path))
        rom = render_rom(result)
        assert f"— {config.indicator.asset}" in rom  # asset shown in ROM title

    exit_code = run_measure("2026-06", CONFIG_DIR, tmp_path, tmp_path / "roms")

    assert exit_code == 0
    roms_dir = tmp_path / "roms" / "2026-06"
    assert (roms_dir / "INMS-1.14-FILE-SERVER.md").exists()
    assert (roms_dir / "INMS-1.14-WIFI.md").exists()
    assert (roms_dir / "INMS-1.14-FILE-SERVER.json").exists()
    assert (roms_dir / "INMS-1.14-WIFI.json").exists()


def test_inms_base_and_group_tab_show_one_row_per_asset(tmp_path: Path) -> None:
    _write_csvs(tmp_path)
    summaries = [
        summarize(measure(config, data_dir=_competencia_data_dir(tmp_path)))
        for config in discover_configs(CONFIG_DIR)
    ]

    workbook = build_report_workbook("2026-06", summaries)

    base_sheet = workbook[INMS_BASE_SHEET]
    base_rows = [
        (base_sheet.cell(row=r, column=5).value, base_sheet.cell(row=r, column=3).value)  # Código INMS, Serviço
        for r in range(2, base_sheet.max_row + 1)
    ]
    assert sorted(base_rows) == [("INMS 1.14", "File Server"), ("INMS 1.14", "WI-FI")]

    noc_soc_sheet = workbook["MONITORAMENTO_NOC_SOC"]
    group_rows = [
        (noc_soc_sheet.cell(row=r, column=1).value, noc_soc_sheet.cell(row=r, column=3).value)  # Código, Serviço
        for r in range(2, noc_soc_sheet.max_row + 1)
    ]
    assert sorted(group_rows) == [("INMS 1.14", "File Server"), ("INMS 1.14", "WI-FI")]

    # each asset kept its own computed result, not collapsed into one
    results = {
        base_sheet.cell(row=r, column=3).value: base_sheet.cell(row=r, column=12).value  # Serviço -> Resultado
        for r in range(2, base_sheet.max_row + 1)
    }
    assert results["File Server"] == pytest.approx(99.80)
    assert results["WI-FI"] == pytest.approx(98.90)

