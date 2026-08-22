"""INMS 1.10 (`count_difference`): real `/input/inms-001-10.csv` is empty
(header only, same open dataset-schema question as INMS 1.8 — ticket 11), so
its acceptance test only proves the pipeline runs against the real file
without breaking. The penalty math itself is proven by a synthetic fixture.
"""

from pathlib import Path

import pytest

from pyauditor.config.models import CountDifferenceAcceptanceExpected
from pyauditor.engine.pipeline import load_config, measure
from pyauditor.rom.render import render_rom

REPO_ROOT = Path(__file__).parent.parent
CONFIG_PATH = REPO_ROOT / "tests" / "fixtures" / "configs" / "inms-1.10.yaml"
INPUT_DIR = REPO_ROOT / "input"


@pytest.mark.skipif(
    not (INPUT_DIR / "inms-001-10.csv").exists(),
    reason="production data (/input) not present locally",
)
def test_inms_1_10_matches_acceptance_test() -> None:
    config = load_config(CONFIG_PATH)
    assert config.acceptance_test is not None
    expected = config.acceptance_test.expected
    assert isinstance(expected, CountDifferenceAcceptanceExpected)

    result = measure(config, data_dir=INPUT_DIR)

    assert result.calculation.memoria["QRC"] == expected.qrc
    assert result.calculation.memoria["QCSI"] == expected.qcsi
    assert result.calculation.memoria["CNI"] == expected.cni
    assert result.calculation.conforms == expected.conforms
    assert result.calculation.penalty_points == pytest.approx(expected.penalty_points)


@pytest.mark.skipif(
    not (INPUT_DIR / "inms-001-10.csv").exists(),
    reason="production data (/input) not present locally",
)
def test_inms_1_10_rom_renders_cni_terms() -> None:
    config = load_config(CONFIG_PATH)
    result = measure(config, data_dir=INPUT_DIR)

    rom = render_rom(result)

    assert "# ROM — INMS 1.10" in rom
    assert "QRC" in rom
    assert "QCSI" in rom
    assert "CNI" in rom


def test_count_difference_penalty_is_fixed_per_missing_unit(tmp_path: Path) -> None:
    config_yaml = """
indicator:
  id: INMS-TEST-1.10
  contractual_id: "INMS TEST 1.10"
  name: Indicador sintético de controles

scope:
  contract: "40/2022 - Ministério da Cultura"
  orgao: MinC

source:
  csv: data.csv
  delimiter: ";"
  encoding: utf-8

quality_gates:
  checks: []

calculation:
  shape: count_difference
  implemented_filter: {column: "Implantado", equals: "S"}
  penalty_per_unit: 1000

target:
  operator: ">="
  value: 100.0
"""
    (tmp_path / "config.yaml").write_text(config_yaml, encoding="utf-8")
    # QRC = 5 recommended controls, QCSI = 3 implemented -> CNI = 2 -> 2000 pontos
    (tmp_path / "data.csv").write_text(
        "Controle;Implantado\nMFA;S\nWAF;S\nSIEM;S\nDLP;N\nEDR;N\n",
        encoding="utf-8",
    )

    config = load_config(tmp_path / "config.yaml")
    result = measure(config, data_dir=tmp_path)

    assert result.calculation.memoria == {"QRC": 5, "QCSI": 3, "CNI": 2}
    assert result.calculation.conforms is False
    assert result.calculation.penalty_points == pytest.approx(2000.0)
    assert result.calculation.result_pct == pytest.approx(60.0)


def test_count_difference_conforms_when_all_recommended_controls_implemented(
    tmp_path: Path,
) -> None:
    config_yaml = """
indicator:
  id: INMS-TEST-1.10-CONFORME
  contractual_id: "INMS TEST 1.10 conforme"
  name: Indicador sintético conforme

scope:
  contract: "40/2022 - Ministério da Cultura"
  orgao: MinC

source:
  csv: data.csv
  delimiter: ";"
  encoding: utf-8

quality_gates:
  checks: []

calculation:
  shape: count_difference
  implemented_filter: {column: "Implantado", equals: "S"}
  penalty_per_unit: 1000

target:
  operator: ">="
  value: 100.0
"""
    (tmp_path / "config.yaml").write_text(config_yaml, encoding="utf-8")
    (tmp_path / "data.csv").write_text("Controle;Implantado\nMFA;S\nWAF;S\n", encoding="utf-8")

    config = load_config(tmp_path / "config.yaml")
    result = measure(config, data_dir=tmp_path)

    assert result.calculation.memoria == {"QRC": 2, "QCSI": 2, "CNI": 0}
    assert result.calculation.conforms is True
    assert result.calculation.penalty_points == pytest.approx(0.0)
