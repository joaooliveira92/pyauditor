from __future__ import annotations

from collections.abc import Mapping
from typing import assert_type

import pytest
from pydantic import ValidationError

from pyauditor.config.models import (
    Calculation,
    ColumnEquals,
    IndicatorConfig,
    RatioCalculation,
)


def test_ratio_count_distinct_requires_filter() -> None:
    with pytest.raises(ValidationError):
        RatioCalculation(
            shape='ratio', aggregation='count_distinct'
        )  # missing numerator_filter


def test_ratio_sum_requires_columns() -> None:
    with pytest.raises(ValidationError):
        RatioCalculation(shape='ratio', aggregation='sum')


def test_ratio_sum_rejects_both_extra_and_subtract_columns() -> None:
    with pytest.raises(ValidationError):
        RatioCalculation(
            shape='ratio',
            aggregation='sum',
            sum_numerator_column='A',
            sum_denominator_extra_column='B',
            sum_numerator_subtract_column='C',
        )


def test_ratio_sum_accepts_subtract_column_alone() -> None:
    RatioCalculation(
        shape='ratio',
        aggregation='sum',
        sum_numerator_column='A',
        sum_numerator_subtract_column='B',
    )


def test_frozen_extra_forbid() -> None:
    m = ColumnEquals(column='a', equals='b')
    with pytest.raises(ValidationError):
        m.column = 'c'  # frozen
    with pytest.raises(ValidationError):
        ColumnEquals(column='a', equals='b', extra='x')  # type: ignore[call-arg]


def test_indicator_config_target_shape() -> None:
    base = dict(
        indicator=dict(id='1.1', contractual_id='INMS 1.1', name='n'),
        scope=dict(contract='c'),
        source=dict(csv='a.csv'),
        quality_gates=dict(checks=[]),
        calculation=dict(
            shape='ratio',
            aggregation='count_distinct',
            numerator_filter=dict(column='c', equals='v'),
        ),
        target=dict(operator='>=', value=90),
        penalty=dict(step_points=1, step_size_pct=0.1),
    )
    cfg = IndicatorConfig.model_validate(base)
    assert_type(cfg.calculation, Calculation)
    # external_catalog_sum must not have target
    bad = {
        **base,
        'calculation': dict(
            shape='external_catalog_sum',
            occurrence_id_column='id',
            catalog_codes_column='codes',
        ),
    }
    with pytest.raises(ValidationError):
        IndicatorConfig.model_validate(bad)


def test_filter_smart_union() -> None:
    r = RatioCalculation.model_validate(
        dict(
            shape='ratio',
            aggregation='count_distinct',
            numerator_filter=dict(column='c', contains='x'),
        )
    )
    assert isinstance(r.numerator_filter, ColumnEquals) is False


def test_source_requires_exactly_one_of_dataset_or_csv() -> None:
    from pyauditor.config.models import Source

    Source(dataset='d', delimiter=';', encoding='utf-8')  # ok
    Source(csv='a.csv', delimiter=';', encoding='utf-8')  # ok
    with pytest.raises(
        ValidationError, match="exactly one of 'dataset' or 'csv'"
    ):
        Source()
    with pytest.raises(
        ValidationError, match="exactly one of 'dataset' or 'csv'"
    ):
        Source(dataset='d', csv='a.csv', delimiter=';', encoding='utf-8')


def test_ratio_precomputed_requires_result_column() -> None:
    with pytest.raises(
        ValidationError, match='precomputed requires precomputed_result_column'
    ):
        RatioCalculation(shape='ratio', aggregation='precomputed')


def _base_indicator_config(
    calculation: Mapping[str, object],
) -> dict[str, object]:
    return {
        'indicator': dict(id='1.1', contractual_id='INMS 1.1', name='n'),
        'scope': dict(contract='c'),
        'source': dict(csv='a.csv'),
        'quality_gates': dict(checks=[]),
        'calculation': calculation,
        'target': dict(operator='>=', value=90),
        'penalty': dict(step_points=1, step_size_pct=0.1),
    }


def test_indicator_config_requires_target_for_non_external_shapes() -> None:
    calc = dict(
        shape='ratio',
        aggregation='count_distinct',
        numerator_filter=dict(column='c', equals='v'),
    )
    base = _base_indicator_config(calc)
    base.pop('target')
    with pytest.raises(ValidationError, match='requires target'):
        IndicatorConfig.model_validate(base)


def test_indicator_config_precomputed_percent_requires_penalty() -> None:
    calc = dict(
        shape='precomputed_table',
        result_column='r',
        result_is_percent=True,
    )
    base = _base_indicator_config(calc)
    base.pop('penalty')
    with pytest.raises(
        ValidationError,
        match='precomputed_table \\(percent\\) requires penalty',
    ):
        IndicatorConfig.model_validate(base)
