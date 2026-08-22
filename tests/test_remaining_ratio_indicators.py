"""INMS 1.3-1.14 (excluding 1.2/1.8/1.10, covered elsewhere): the remaining
`ratio`-shaped indicators, one real acceptance_test each, exercising all 3
`aggregation` variants (count_distinct, sum, precomputed). See ticket 07.

1.3, 1.9 have empty real CSVs (same fog as 1.8/1.10 — no data rows), so their
acceptance tests are degenerate; the `sum` aggregation's actual math is
proven by a synthetic fixture in this file instead.
"""

from pathlib import Path

import pytest

from pyauditor.config.models import RatioAcceptanceExpected
from pyauditor.engine.pipeline import load_config, measure

REPO_ROOT = Path(__file__).parent.parent
CONFIG_DIR = REPO_ROOT / 'tests' / 'fixtures' / 'configs'
INPUT_DIR = REPO_ROOT / 'input'

INDICATORS = [
    ('inms-1.3.yaml', 'inms-001-03.csv'),
    ('inms-1.4.yaml', 'inms-001-04.csv'),
    ('inms-1.5.yaml', 'inms-001-05.csv'),
    ('inms-1.6.yaml', 'inms-001-06.csv'),
    ('inms-1.7.yaml', 'inms-001-07.csv'),
    ('inms-1.9.yaml', 'inms-001-09.csv'),
    ('inms-1.11.yaml', 'inms-001-11.csv'),
    ('inms-1.12.yaml', 'inms-001-12.csv'),
    ('inms-1.13.yaml', 'inms-001-13.csv'),
    ('inms-1.14.yaml', 'inms-001-14.csv'),
]


@pytest.mark.parametrize(
    'config_file,csv_file', INDICATORS, ids=[c for c, _ in INDICATORS]
)
def test_indicator_matches_acceptance_test(
    config_file: str, csv_file: str
) -> None:
    if not (INPUT_DIR / csv_file).exists():
        pytest.skip('production data (/input) not present locally')

    config = load_config(CONFIG_DIR / config_file)
    assert config.acceptance_test is not None
    expected = config.acceptance_test.expected
    assert isinstance(expected, RatioAcceptanceExpected)

    result = measure(config, data_dir=INPUT_DIR)

    assert result.calculation.memoria['numerator'] == pytest.approx(
        expected.numerator
    )
    assert result.calculation.memoria['denominator'] == pytest.approx(
        expected.denominator
    )
    assert result.calculation.result_pct == pytest.approx(
        expected.result_pct, abs=0.01
    )
    assert result.calculation.conforms == expected.conforms
    assert result.calculation.penalty_points == pytest.approx(
        expected.penalty_points, abs=0.01
    )


def test_sum_aggregation_computes_dpe_over_dpe_plus_da(tmp_path: Path) -> None:
    """INMS 1.3's shape: ΣDPE / (ΣDPE + ΣDA) x 100. Real data is empty (see
    module docstring), so this proves the `sum` math directly.
    """
    config_yaml = """
indicator:
  id: INMS-TEST-1.3
  contractual_id: "INMS TEST 1.3"
  name: Indicador sintético de soma

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
  shape: ratio
  aggregation: sum
  sum_numerator_column: "DiasProjeto"
  sum_denominator_extra_column: "DiasAtraso"

target:
  operator: ">="
  value: 100.0

penalty:
  step_points: 200
  step_size_pct: 1.0
"""
    (tmp_path / 'config.yaml').write_text(config_yaml, encoding='utf-8')
    # 3 projetos: DPE totals 270, DA totals 30 -> 270/(270+30) = 90%
    (tmp_path / 'data.csv').write_text(
        'Projeto;DiasProjeto;DiasAtraso\nP1;90;10\nP2;90;10\nP3;90;10\n',
        encoding='utf-8',
    )

    config = load_config(tmp_path / 'config.yaml')
    result = measure(config, data_dir=tmp_path)

    assert result.calculation.memoria == {
        'numerator': 270.0,
        'denominator': 300.0,
    }
    assert result.calculation.result_pct == pytest.approx(90.0)
    assert result.calculation.conforms is False
    # shortfall 10 p.p. / 1% step * 200 = 2000
    assert result.calculation.penalty_points == pytest.approx(2000.0)


def test_sum_aggregation_parses_pt_br_comma_decimals(tmp_path: Path) -> None:
    """The real datasets are PT-BR exports (comma decimal separator) — the
    `sum` aggregation must route through `parse_decimal`, not bare `float()`,
    same as every other numeric-reading strategy."""
    config_yaml = """
indicator:
  id: INMS-TEST-1.3-DECIMAL
  contractual_id: "INMS TEST 1.3 decimal"
  name: Indicador sintético de soma com decimal PT-BR

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
  shape: ratio
  aggregation: sum
  sum_numerator_column: "DiasProjeto"
  sum_denominator_extra_column: "DiasAtraso"

target:
  operator: ">="
  value: 100.0

penalty:
  step_points: 200
  step_size_pct: 1.0
"""
    (tmp_path / 'config.yaml').write_text(config_yaml, encoding='utf-8')
    # Comma-decimal values ("90,5") — bare float() raises ValueError on these.
    (tmp_path / 'data.csv').write_text(
        'Projeto;DiasProjeto;DiasAtraso\nP1;90,5;10,5\n', encoding='utf-8'
    )

    config = load_config(tmp_path / 'config.yaml')
    result = measure(config, data_dir=tmp_path)

    assert result.calculation.memoria == {
        'numerator': 90.5,
        'denominator': 101.0,
    }


def test_sum_aggregation_subtracts_and_excludes_a_totals_row(
    tmp_path: Path,
) -> None:
    """INMS 1.6's shape: (ΣCA - ΣCR) / ΣCA x 100, with a "TOTAIS" row that
    must be excluded (via `denominator_filter` reused as the eligible-rows
    filter) — summing it alongside the per-agreement rows would double-count,
    and the real CSV's "TOTAIS" row formats its counts with a thousands
    separator ("1.622"), which `float()` would silently misparse as 1.622.
    """
    config_yaml = """
indicator:
  id: INMS-TEST-1.6
  contractual_id: "INMS TEST 1.6"
  name: Indicador sintético de subtração

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
  shape: ratio
  aggregation: sum
  denominator_filter:
    column: "Acordo"
    not_equals: "TOTAIS"
  sum_numerator_column: "Total de Chamados"
  sum_numerator_subtract_column: "Total de Chamados Reabertos"

target:
  operator: ">="
  value: 97.0

penalty:
  step_points: 200
  step_size_pct: 0.5
"""
    (tmp_path / 'config.yaml').write_text(config_yaml, encoding='utf-8')
    (tmp_path / 'data.csv').write_text(
        'Acordo;Total de Chamados;Total de Chamados Reabertos\n'
        'SLA A;79;0\n'
        'SLA B;8;1\n'
        'TOTAIS;1.087;999\n',  # thousands-separated + wrong — must be ignored
        encoding='utf-8',
    )

    config = load_config(tmp_path / 'config.yaml')
    result = measure(config, data_dir=tmp_path)

    assert result.calculation.memoria == {
        'numerator': 86.0,
        'denominator': 87.0,
    }
    assert result.calculation.conforms is True
    assert result.calculation.penalty_points == pytest.approx(0.0)


def test_precomputed_aggregation_reads_result_directly_from_the_single_row(
    tmp_path: Path,
) -> None:
    config_yaml = """
indicator:
  id: INMS-TEST-PRECOMPUTED
  contractual_id: "INMS TEST precomputed"
  name: Indicador sintético pré-agregado

scope:
  contract: "40/2022 - Ministério da Cultura"
  orgao: MinC

source:
  csv: data.csv
  delimiter: ","
  encoding: utf-8

quality_gates:
  checks: []

calculation:
  shape: ratio
  aggregation: precomputed
  precomputed_result_column: "Disponibilidade Realizada (%)"

target:
  operator: ">="
  value: 99.5

penalty:
  step_points: 1000
  step_size_pct: 0.1
"""
    (tmp_path / 'config.yaml').write_text(config_yaml, encoding='utf-8')
    (tmp_path / 'data.csv').write_text(
        'Descrição,Disponibilidade Realizada (%)\nServiço X,99.2\n',
        encoding='utf-8',
    )

    config = load_config(tmp_path / 'config.yaml')
    result = measure(config, data_dir=tmp_path)

    assert result.calculation.result_pct == pytest.approx(99.2)
    assert result.calculation.conforms is False
    # shortfall 0.3 p.p. / 0.1% step * 1000 = 3000
    assert result.calculation.penalty_points == pytest.approx(3000.0)
