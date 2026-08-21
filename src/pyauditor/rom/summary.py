"""Flattens a `MeasurementResult` into a shape-agnostic, serializable
summary — the structured counterpart to the ROM's prose Markdown, consumed
by `report` (ticket 09) to build the consolidated Excel without re-parsing
Markdown.
"""

from dataclasses import asdict, dataclass, fields

from pyauditor.engine.pipeline import MeasurementResult
from pyauditor.engine.strategies import SHAPE_REGISTRY

_STR_FIELDS: tuple[str, ...] = ("indicator_id", "contractual_id", "name", "orgao", "shape")
_OPTIONAL_STR_FIELDS: tuple[str, ...] = ("asset", "target_operator")
_NUMERIC_FIELDS: tuple[str, ...] = ("result_pct", "penalty_points")
_OPTIONAL_NUMERIC_FIELDS: tuple[str, ...] = ("target_value", "numerator", "denominator")
_BOOL_FIELDS: tuple[str, ...] = ("conforms", "hard_failure", "systematic_failure")


@dataclass(frozen=True)
class IndicatorSummary:
    """Round-trips through JSON (`to_dict()` / `IndicatorSummary(**raw)`) as
    the sidecar `report`/`consolidate` read back — a stale or hand-edited
    sidecar with a wrong-typed field is rejected here, at load time, rather
    than crashing deep in `excel/report.py`/`excel/consolidate.py` arithmetic."""

    indicator_id: str
    contractual_id: str
    name: str
    asset: str | None
    orgao: str
    shape: str
    target_operator: str | None
    target_value: float | None
    result_pct: float
    conforms: bool
    penalty_points: float
    numerator: float | None
    denominator: float | None
    hard_failure: bool
    systematic_failure: bool = False

    def __post_init__(self) -> None:
        known_fields = {f.name for f in fields(self)}
        for name in _STR_FIELDS:
            assert name in known_fields
            _require_str(self, name)
        for name in _OPTIONAL_STR_FIELDS:
            _require_str(self, name, optional=True)
        for name in _NUMERIC_FIELDS:
            _require_numeric(self, name)
        for name in _OPTIONAL_NUMERIC_FIELDS:
            _require_numeric(self, name, optional=True)
        for name in _BOOL_FIELDS:
            _require_bool(self, name)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _require_str(summary: "IndicatorSummary", name: str, *, optional: bool = False) -> None:
    value: object = getattr(summary, name)
    if optional and value is None:
        return
    if not isinstance(value, str):
        raise TypeError(f"IndicatorSummary.{name} must be str, got {type(value).__name__}")


def _require_numeric(summary: "IndicatorSummary", name: str, *, optional: bool = False) -> None:
    import math

    value: object = getattr(summary, name)
    if optional and value is None:
        return
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError(
            f"IndicatorSummary.{name} must be a number, got {type(value).__name__}"
        )
    if not math.isfinite(float(value)):
        raise ValueError(
            f"IndicatorSummary.{name} não finito ({value!r}) — sidecar JSON com NaN/Infinity"
        )


def _require_bool(summary: "IndicatorSummary", name: str) -> None:
    value: object = getattr(summary, name)
    if not isinstance(value, bool):
        raise TypeError(f"IndicatorSummary.{name} must be bool, got {type(value).__name__}")


def summarize(result: MeasurementResult) -> IndicatorSummary:
    config = result.config
    calculation = result.calculation
    shape = config.calculation.shape

    numerator, denominator = _pooled_numerator_denominator(shape, calculation.memoria)

    return IndicatorSummary(
        indicator_id=config.indicator.id,
        contractual_id=config.indicator.contractual_id,
        name=config.indicator.name,
        asset=config.indicator.asset,
        orgao=config.scope.orgao,
        shape=shape,
        target_operator=config.target.operator if config.target is not None else None,
        target_value=config.target.value if config.target is not None else None,
        result_pct=calculation.result_pct,
        conforms=calculation.conforms,
        penalty_points=calculation.penalty_points,
        numerator=numerator,
        denominator=denominator,
        hard_failure=result.hard_failure,
        systematic_failure=result.systematic_failure,
    )


def _pooled_numerator_denominator(
    shape: str, memoria: dict[str, object]
) -> tuple[float | None, float | None]:
    """Delegates to the shape's own strategy (`SHAPE_REGISTRY`, the same
    registry `engine.pipeline.measure` dispatches on) instead of a second,
    separately-maintained shape-keyed dispatch — one place to update when a
    shape is added, not two."""
    strategy = SHAPE_REGISTRY.get(shape)
    if strategy is None:
        return None, None
    return strategy.pool_numerator_denominator(memoria)
