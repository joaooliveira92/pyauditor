"""`precomputed_table` shape: proves the aggregated-apuração reading — PT-BR
comma decimals, per-ativo `penalidade_pontos` read from the dataset,
hours-weighted headline, and the points mode (INMS 1.8). All synthetic.
"""

from pathlib import Path

import pytest

from pyauditor.config.models import (
    IndicatorConfig,
    PrecomputedTableAcceptanceExpected,
)
from pyauditor.engine.pipeline import load_config, measure
from pyauditor.rom.render import render_rom

REPO_ROOT = Path(__file__).parent.parent
CONFIG_PATH = REPO_ROOT / 'tests' / 'fixtures' / 'configs' / 'inms-1.4.yaml'
INPUT_DIR = REPO_ROOT / 'input' / '2026' / '06'


@pytest.mark.skipif(
    not (INPUT_DIR / 'inms-04.csv').exists(), reason='dados locais ausentes'
)
def test_inms_1_4_matches_acceptance_test() -> None:
    config = load_config(CONFIG_PATH)
    assert config.acceptance_test is not None
    expected = config.acceptance_test.expected
    assert isinstance(expected, PrecomputedTableAcceptanceExpected)

    result = measure(config, data_dir=INPUT_DIR)
    calc = result.calculation

    assert calc.result_pct == pytest.approx(expected.result_pct, abs=0.01)
    assert calc.conforms == expected.conforms
    assert calc.penalty_points == pytest.approx(
        expected.penalty_points, abs=0.01
    )
    categories = calc.memoria['categories']
    assert isinstance(categories, list)
    assert len(categories) == 5  # per-ativo rows, garbage rows skipped


@pytest.mark.skipif(
    not (INPUT_DIR / 'inms-04.csv').exists(), reason='dados locais ausentes'
)
def test_inms_1_4_rom_renders_per_asset_table() -> None:
    config = load_config(CONFIG_PATH)
    result = measure(config, data_dir=INPUT_DIR)

    rom = render_rom(result)

    assert '# ROM — INMS 1.04' in rom
    assert '| Ativo | Resultado | Penalidade |' in rom
    assert (
        'Barramento de Integracao' in rom or 'Barramento de Integração' in rom
    )


def test_precomputed_table_skips_empty_rows_and_parses_comma_decimals(
    tmp_path: Path,
) -> None:
    """PT-BR export reality: `;`-delimited, comma decimals, trailing `;` rows
    that carry no measurement (see inms-13.csv)."""
    config_yaml = """
indicator:
  id: INMS-TEST-PT
  contractual_id: "INMS TEST PT"
  name: Tabela sintética

scope:
  contract: "40/2022 - MinC"
  orgao: MinC

source:
  csv: data.csv
  delimiter: ";"
  encoding: utf-8

quality_gates:
  checks: []

calculation:
  shape: precomputed_table
  result_column: resultado
  name_column: ativo
  numerator_column: numerador
  denominator_column: base
  penalty_column: penalidade

target:
  operator: ">="
  value: 95.5

penalty:
  step_points: 1000
  step_size_pct: 0.1
"""
    config_dir = tmp_path
    (config_dir / 'config.yaml').write_text(config_yaml, encoding='utf-8')
    (config_dir / 'data.csv').write_text(
        'ativo;resultado;numerador;base;penalidade\n'
        'A;99,25;198,5;200;0\n'
        'B;95,10;190,2;200;1000\n'
        ';;;;\n'  # empty/placeholder row — must be skipped, not crash
        'C;;0;0;0\n',  # empty result — skipped
        encoding='utf-8',
    )

    config = load_config(config_dir / 'config.yaml')
    assert isinstance(config, IndicatorConfig)
    calc = measure(config, data_dir=config_dir).calculation

    categories = calc.memoria['categories']
    assert isinstance(categories, list)
    assert [c['name'] for c in categories] == ['A', 'B']

    # pooled headline = 100 * Σ(numerador)/Σ(base)
    assert calc.result_pct == pytest.approx(
        (198.5 + 190.2) / 400.0 * 100.0, abs=0.01
    )
    assert calc.penalty_points == pytest.approx(1000.0)
    assert calc.conforms is False


def test_precomputed_table_points_mode_reads_excess_over_meta(
    tmp_path: Path,
) -> None:
    """INMS 1.8-style point sum: value vs point meta, penalty = excess."""
    config_yaml = """
indicator:
  id: IND-TEST-PONTOS
  contractual_id: "INMS TEST PONTOS"
  name: Sato

scope:
  contract: "40/2022 - MinC"
  orgao: MinC

source:
  csv: data.csv
  delimiter: ";"
  encoding: "utf-8"

quality_gates:
  checks: []

calculation:
  shape: precomputed_table
  result_column: total_pdt
  result_is_percent: false
  penalty_column: excesso

target:
  operator: ">="
  value: 0.0
"""
    config_dir = tmp_path
    (config_dir / 'config.yaml').write_text(config_yaml, encoding='utf-8')
    (config_dir / 'data.csv').write_text(
        'servico;total_pdt;excesso\nSRV-1;0;2\nSRV-2;0;0\n',
        encoding='utf-8',
    )

    config = load_config(config_dir / 'config.yaml')
    assert isinstance(config, IndicatorConfig)
    result = measure(config, data_dir=config_dir).calculation

    assert result.result_pct == 0.0
    assert result.penalty_points == pytest.approx(2.0)
    assert result.conforms is False
