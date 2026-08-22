"""INMS 1.2 (`segmented_ratio`): real acceptance test (all-conforming) plus a
synthetic fixture that exercises the linear penalty math a conforming dataset
can't reach.
"""

from pathlib import Path

import pytest

from pyauditor.config.models import (
    IndicatorConfig,
    SegmentedRatioAcceptanceExpected,
)
from pyauditor.engine.pipeline import load_config, measure
from pyauditor.rom.render import render_rom

REPO_ROOT = Path(__file__).parent.parent
CONFIG_PATH = REPO_ROOT / 'tests' / 'fixtures' / 'configs' / 'inms-1.2.yaml'
INPUT_DIR = REPO_ROOT / 'input'


@pytest.mark.skipif(
    not (INPUT_DIR / 'inms-001-02.csv').exists(),
    reason='production data (/input) not present locally',
)
def test_inms_1_2_matches_acceptance_test() -> None:
    config = load_config(CONFIG_PATH)
    assert config.acceptance_test is not None
    expected = config.acceptance_test.expected
    assert isinstance(expected, SegmentedRatioAcceptanceExpected)

    result = measure(config, data_dir=INPUT_DIR)
    categories = result.calculation.memoria['categories']
    assert isinstance(categories, list)

    assert result.calculation.result_pct == pytest.approx(
        expected.result_pct, abs=0.01
    )
    assert result.calculation.conforms == expected.conforms
    assert result.calculation.penalty_points == pytest.approx(
        expected.penalty_points, abs=0.01
    )

    for actual_category, expected_category in zip(
        categories, expected.categories, strict=True
    ):
        assert actual_category['name'] == expected_category.name
        assert actual_category['numerator'] == expected_category.numerator
        assert actual_category['denominator'] == expected_category.denominator
        assert actual_category['result_pct'] == pytest.approx(
            expected_category.result_pct, abs=0.01
        )
        assert actual_category['penalty_points'] == pytest.approx(
            expected_category.penalty_points, abs=0.01
        )


@pytest.mark.skipif(
    not (INPUT_DIR / 'inms-001-02.csv').exists(),
    reason='production data (/input) not present locally',
)
def test_inms_1_2_rom_renders_category_table() -> None:
    config = load_config(CONFIG_PATH)
    result = measure(config, data_dir=INPUT_DIR)

    rom = render_rom(result)

    assert '# ROM — INMS 1.02' in rom
    assert (
        '| Categoria | Numerador | Denominador | Resultado | Penalidade |'
        in rom
    )
    assert 'alta' in rom
    assert 'media' in rom
    assert 'baixa' in rom


def test_segmented_ratio_penalty_sums_underperforming_categories(
    tmp_path: Path,
) -> None:
    """Synthetic fixture: real INMS 1.2 data conforms on all 3 categories, so
    it can't prove the penalty math. This one puts "alta" below target.
    """
    config_yaml = """
indicator:
  id: INMS-TEST-1.2
  contractual_id: "INMS TEST 1.2"
  name: Indicador sintético segmentado

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
  shape: segmented_ratio
  step_size_pct: 0.1
  categories:
    - name: alta
      denominator_filter: {column: "SLA", contains: "Alta"}
      numerator_filter: {column: "No prazo", equals: "S"}
      step_points: 20
    - name: baixa
      denominator_filter: {column: "SLA", contains: "Baixa"}
      numerator_filter: {column: "No prazo", equals: "S"}
      step_points: 10

target:
  operator: ">="
  value: 90.0
"""
    config_dir = tmp_path
    (config_dir / 'config.yaml').write_text(config_yaml, encoding='utf-8')
    (config_dir / 'data.csv').write_text(
        'Nº Solicitacao;SLA;No prazo\n'
        '1;Alta;S\n'
        '2;Alta;N\n'  # alta: 1/2 = 50% -> 40 p.p. shortfall -> 40/0.1*20 = 8000
        '3;Baixa;S\n'
        '4;Baixa;S\n',  # baixa: 2/2 = 100% -> conforms, 0 penalty
        encoding='utf-8',
    )

    config = load_config(config_dir / 'config.yaml')
    assert isinstance(config, IndicatorConfig)
    result = measure(config, data_dir=config_dir)

    raw_categories = result.calculation.memoria['categories']
    assert isinstance(raw_categories, list)
    categories = {c['name']: c for c in raw_categories}
    assert categories['alta']['penalty_points'] == pytest.approx(8000.0)
    assert categories['baixa']['penalty_points'] == pytest.approx(0.0)
    assert result.calculation.penalty_points == pytest.approx(8000.0)
    assert result.calculation.conforms is False
