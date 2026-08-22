"""Per-órgão config contract: configs live under `configs/<órgão>/`, and
discovery validates `scope.orgao` against the órgão being driven (mismatch =
hard error, so a misplaced config can't silently distort consolidation).
"""

from pathlib import Path

import pytest

from pyauditor.config.models import IndicatorConfig
from pyauditor.engine.pipeline import discover_configs

MINC_ORG = "MinC"
MTUR_ORG = "MTur"

CONFIG_YAML = """\
indicator:
  id: INMS-TEST
  contractual_id: "INMS TEST"
  name: Indicador sintético

scope:
  contract: "40/2022 - Ministério Cultura"
  orgao: {orgao}

source:
  dataset: test_data

quality_gates:
  checks: []

calculation:
  shape: ratio
  aggregation: count_distinct
  numerator_filter:
    column: "Espera"
    max_seconds: 20

target:
  operator: ">="
  value: 95.0

penalty:
  step_points: 10
  step_size_pct: 1.0
"""


def _write_orgao_config(config_dir: Path, orgao: str, filename: str) -> None:
    (config_dir / orgao).mkdir(parents=True, exist_ok=True)
    (config_dir / orgao / filename).write_text(CONFIG_YAML.format(orgao=orgao), encoding="utf-8")


def test_discover_configs_finds_per_orgao_dir(tmp_path: Path) -> None:
    _write_orgao_config(tmp_path, MINC_ORG, "inms-1.yaml")
    _write_orgao_config(tmp_path, MTUR_ORG, "inms-2.yaml")

    minc = discover_configs(tmp_path / MINC_ORG)
    mtur = discover_configs(tmp_path / MTUR_ORG)

    assert [c.indicator.id for c in minc] == ["INMS-TEST"]
    assert minc[0].scope.orgao == MINC_ORG
    assert mtur[0].scope.orgao == MTUR_ORG


def test_discover_configs_accepts_matching_expected_orgao(tmp_path: Path) -> None:
    _write_orgao_config(tmp_path, MINC_ORG, "inms-1.yaml")

    configs = discover_configs(tmp_path / MINC_ORG, expected_orgao=MINC_ORG)

    assert isinstance(configs[0], IndicatorConfig)


def test_discover_orgao_mismatch_is_a_hard_error(tmp_path: Path) -> None:
    """A config that says MTur but sits in the MinC dir must fail loudly rather
    than silently feed MTur rules (or orgao) into a MinC run."""
    (tmp_path / MTUR_ORG).mkdir(parents=True, exist_ok=True)
    (tmp_path / MINC_ORG).mkdir(parents=True, exist_ok=True)
    (tmp_path / MINC_ORG / "misplaced.yaml").write_text(
        CONFIG_YAML.format(orgao=MTUR_ORG), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="não corresponde"):
        discover_configs(tmp_path / MINC_ORG, expected_orgao=MINC_ORG)


def test_discover_skips_manifest_in_orgao_dir(tmp_path: Path) -> None:
    _write_orgao_config(tmp_path, MINC_ORG, "inms-1.yaml")
    (tmp_path / MINC_ORG / "datasets.yaml").write_text(
        "datasets:\n  test_data:\n    file: data.csv\n", encoding="utf-8"
    )

    configs = discover_configs(tmp_path / MINC_ORG, expected_orgao=MINC_ORG)

    assert len(configs) == 1
