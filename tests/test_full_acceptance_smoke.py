"""spec.md §5 — the full 14-indicator smoke test: every real `inms-1.*.yaml`
fixture's `acceptance_test` verified against the real `/input` CSV, driving
the engine directly (no CLI). Complements (doesn't replace) the individual
per-shape tests, which additionally cover synthetic edge cases the real
data can't reach.
"""

from pathlib import Path

import pytest

from pyauditor.config.models import (
    CountDifferenceAcceptanceExpected,
    ExternalCatalogSumAcceptanceExpected,
    IndicatorConfig,
    PrecomputedTableAcceptanceExpected,
    RatioAcceptanceExpected,
    SegmentedRatioAcceptanceExpected,
)
from pyauditor.engine.pipeline import discover_configs, measure

REPO_ROOT = Path(__file__).parent.parent
CONFIG_DIR = REPO_ROOT / 'tests' / 'fixtures' / 'configs'
# Datasets live under <data-dir>/<competência>/ — the smoke test validates
# against the real data of one competência (see `cli/measure.py`).
INPUT_DIR = REPO_ROOT / 'input' / '2026' / '06'

_ALL_CONFIGS: list[IndicatorConfig] = discover_configs(CONFIG_DIR)


def _config_id(config: IndicatorConfig) -> str:
    return config.indicator.contractual_id


@pytest.mark.skipif(
    not INPUT_DIR.exists(),
    reason='production data (/input) not present locally',
)
@pytest.mark.parametrize('config', _ALL_CONFIGS, ids=_config_id)
def test_acceptance_test_matches_real_data(config: IndicatorConfig) -> None:
    assert config.acceptance_test is not None, (
        f'{_config_id(config)}: config has no acceptance_test'
    )
    expected = config.acceptance_test.expected
    label = _config_id(config)

    result = measure(config, data_dir=INPUT_DIR)
    calc = result.calculation

    assert calc.result_pct == pytest.approx(expected.result_pct, abs=0.01), (
        f'{label}: result_pct — expected {expected.result_pct}, got'
        f'{calc.result_pct}'
    )
    assert calc.conforms == expected.conforms, (
        f'{label}: conforms — expected {expected.conforms}, got {calc.conforms}'
    )
    assert calc.penalty_points == pytest.approx(
        expected.penalty_points, abs=0.01
    ), (
        f'{label}: penalty_points — expected {expected.penalty_points}, got'
        f'{calc.penalty_points}'
    )

    if isinstance(expected, RatioAcceptanceExpected):
        assert calc.memoria.get('numerator') == pytest.approx(
            expected.numerator
        ), (
            f'{label}: numerator — expected {expected.numerator}, '
            f'got {calc.memoria.get("numerator")}'
        )
        assert calc.memoria.get('denominator') == pytest.approx(
            expected.denominator
        ), (
            f'{label}: denominator — expected {expected.denominator}, '
            f'got {calc.memoria.get("denominator")}'
        )

    elif isinstance(expected, SegmentedRatioAcceptanceExpected):
        categories = calc.memoria.get('categories')
        assert isinstance(categories, list), (
            f'{label}: expected categories in memoria, found none'
        )
        for expected_category, actual_category in zip(
            expected.categories, categories, strict=True
        ):
            assert actual_category.get('name') == expected_category.name, (
                f'{label}/{expected_category.name}: category name mismatch'
            )
            assert (
                actual_category.get('numerator') == expected_category.numerator
            ), (
                f'{label}/{expected_category.name}: numerator — '
                f'expected {expected_category.numerator}, '
                f'got {actual_category.get("numerator")}'
            )
            assert (
                actual_category.get('denominator')
                == expected_category.denominator
            ), (
                f'{label}/{expected_category.name}: denominator — '
                f'expected {expected_category.denominator}, '
                f'got {actual_category.get("denominator")}'
            )
            assert actual_category.get('penalty_points') == pytest.approx(
                expected_category.penalty_points
            ), (
                f'{label}/{expected_category.name}: penalty_points — '
                f'expected {expected_category.penalty_points}, '
                f'got {actual_category.get("penalty_points")}'
            )

    elif isinstance(expected, CountDifferenceAcceptanceExpected):
        assert calc.memoria.get('QRC') == expected.qrc, (
            f'{label}: QRC — expected {expected.qrc}, got'
            f'{calc.memoria.get("QRC")}'
        )
        assert calc.memoria.get('QCSI') == expected.qcsi, (
            f'{label}: QCSI — expected {expected.qcsi}, got'
            f'{calc.memoria.get("QCSI")}'
        )
        assert calc.memoria.get('CNI') == expected.cni, (
            f'{label}: CNI — expected {expected.cni}, got'
            f'{calc.memoria.get("CNI")}'
        )

    elif isinstance(expected, ExternalCatalogSumAcceptanceExpected):
        assert calc.memoria.get('total_points') == expected.total_points, (
            f'{label}: total_points — expected {expected.total_points}, '
            f'got {calc.memoria.get("total_points")}'
        )

    elif isinstance(expected, PrecomputedTableAcceptanceExpected):
        # headline result/conforms/penalty are validated above; the per-ativo
        # breakdown is exercised synthetically in
        # tests/test_precomputed_table.py.
        assert isinstance(calc.memoria.get('categories'), list)


def test_all_14_indicators_are_discovered() -> None:
    contractual_ids = {_config_id(config) for config in _ALL_CONFIGS}
    expected_ids = {f'INMS 1.{n}' for n in range(1, 15)}
    assert contractual_ids == expected_ids
