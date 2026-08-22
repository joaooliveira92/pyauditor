from __future__ import annotations

from typing import Any

import pytest

from pyauditor.rom.summary import IndicatorSummary


def _build(**kwargs: object) -> IndicatorSummary:
    # Boundary: tests deliberately pass wrong-typed values to prove
    # __post_init__ rejects them at runtime — basedpyright can't type-check that.
    return IndicatorSummary(**kwargs)  # type: ignore[arg-type]


_VALID_KWARGS: dict[str, Any] = dict(
    indicator_id="INMS-1.1",
    contractual_id="INMS 1.1",
    name="Indicador",
    asset=None,
    orgao="MinC",
    shape="ratio",
    target_operator=">=",
    target_value=98.0,
    result_pct=97.5,
    conforms=False,
    penalty_points=10.0,
    numerator=175.0,
    denominator=180.0,
    hard_failure=False,
)


def test_indicator_summary_accepts_well_typed_fields() -> None:
    summary = _build(**_VALID_KWARGS)
    assert summary.result_pct == 97.5


def test_indicator_summary_round_trips_through_to_dict() -> None:
    summary = _build(**_VALID_KWARGS)
    assert _build(**summary.to_dict()) == summary


@pytest.mark.parametrize(
    "field,bad_value",
    [
        ("result_pct", "97.5"),  # string where a number is expected
        ("result_pct", True),  # bool leaking into a numeric field
        ("penalty_points", None),  # non-optional numeric field can't be None
        ("target_value", "98.0"),  # optional numeric field, wrong type
        ("numerator", True),
        ("conforms", "false"),  # string where bool is expected
        ("conforms", 0),  # int, not bool
        ("indicator_id", None),
        ("orgao", 1),
    ],
)
def test_indicator_summary_rejects_wrong_typed_fields(field: str, bad_value: object) -> None:
    kwargs = dict(_VALID_KWARGS)
    kwargs[field] = bad_value
    with pytest.raises(TypeError, match=field):
        _build(**kwargs)


def test_indicator_summary_allows_none_for_optional_fields() -> None:
    kwargs = dict(_VALID_KWARGS)
    kwargs["asset"] = None
    kwargs["target_operator"] = None
    kwargs["target_value"] = None
    kwargs["numerator"] = None
    kwargs["denominator"] = None
    _build(**kwargs)  # must not raise
