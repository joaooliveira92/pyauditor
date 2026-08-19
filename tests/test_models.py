from __future__ import annotations

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
        RatioCalculation(shape="ratio", aggregation="count_distinct")  # missing numerator_filter

def test_ratio_sum_requires_columns() -> None:
    with pytest.raises(ValidationError):
        RatioCalculation(shape="ratio", aggregation="sum")

def test_frozen_extra_forbid() -> None:
    m = ColumnEquals(column="a", equals="b")
    with pytest.raises(Exception):
        m.column = "c"  # frozen
    with pytest.raises(ValidationError):
        ColumnEquals(column="a", equals="b", extra="x")  # type: ignore[call-arg]

def test_indicator_config_target_shape() -> None:
    base = dict(
        indicator=dict(id="1.1", contractual_id="INMS 1.1", name="n"),
        scope=dict(contract="c"),
        source=dict(csv="a.csv"),
        quality_gates=dict(checks=[]),
        calculation=dict(shape="ratio", aggregation="count_distinct", numerator_filter=dict(column="c", equals="v")),
        target=dict(operator=">=", value=90),
        penalty=dict(step_points=1, step_size_pct=0.1),
    )
    cfg = IndicatorConfig.model_validate(base)
    assert_type(cfg.calculation, Calculation)
    # external_catalog_sum must not have target
    bad = {**base, "calculation": dict(shape="external_catalog_sum", occurrence_id_column="id", catalog_codes_column="codes")}
    with pytest.raises(ValidationError):
        IndicatorConfig.model_validate(bad)

def test_filter_smart_union() -> None:
    r = RatioCalculation.model_validate(
        dict(shape="ratio", aggregation="count_distinct", numerator_filter=dict(column="c", contains="x"))
    )
    assert isinstance(r.numerator_filter, ColumnEquals) is False