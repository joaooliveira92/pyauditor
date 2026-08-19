"""Flattens a `MeasurementResult` into a shape-agnostic, serializable
summary — the structured counterpart to the ROM's prose Markdown, consumed
by `report` (ticket 09) to build the consolidated Excel without re-parsing
Markdown.
"""

from dataclasses import asdict, dataclass

from pyauditor.engine.pipeline import MeasurementResult


@dataclass(frozen=True)
class IndicatorSummary:
    indicator_id: str
    contractual_id: str
    name: str
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

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def summarize(result: MeasurementResult) -> IndicatorSummary:
    config = result.config
    calculation = result.calculation
    shape = config.calculation.shape

    numerator, denominator = _pooled_numerator_denominator(shape, calculation.memoria)

    return IndicatorSummary(
        indicator_id=config.indicator.id,
        contractual_id=config.indicator.contractual_id,
        name=config.indicator.name,
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
    )


def _pooled_numerator_denominator(
    shape: str, memoria: dict[str, object]
) -> tuple[float | None, float | None]:
    if shape == "ratio":
        return _as_float(memoria.get("numerator")), _as_float(memoria.get("denominator"))

    if shape == "segmented_ratio":
        categories = memoria.get("categories")
        if not isinstance(categories, list):
            return None, None
        numerator = sum(_as_float(c.get("numerator")) or 0.0 for c in categories if isinstance(c, dict))
        denominator = sum(_as_float(c.get("denominator")) or 0.0 for c in categories if isinstance(c, dict))
        return numerator, denominator

    if shape == "count_difference":
        return _as_float(memoria.get("QCSI")), _as_float(memoria.get("QRC"))

    # external_catalog_sum: a point sum, not a ratio — no numerator/denominator.
    return None, None


def _as_float(value: object) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    return None
