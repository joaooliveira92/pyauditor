"""Shared contract every calculation strategy implements."""

from dataclasses import dataclass
from typing import Protocol

from pyauditor.config.models import Calculation, IndicatorConfig


@dataclass(frozen=True)
class CalculationResult:
    result_pct: float
    conforms: bool
    penalty_points: float
    memoria: dict[str, object]  # shape-specific values the ROM renderer needs


class CalculationStrategy(Protocol):
    def calculate(
        self, config: IndicatorConfig, rows: list[dict[str, str]]
    ) -> CalculationResult: ...

    def pool_numerator_denominator(
        self, memoria: dict[str, object]
    ) -> tuple[float | None, float | None]:
        """Extracts a headline numerator/denominator from this shape's own
        `memoria` (the ROM/summary layer's pooling question, answered by the
        shape that produced the data — a single source of truth instead of a
        second shape-keyed dispatch living in `rom/summary.py`)."""
        ...


def narrow_calculation[C: Calculation](
    config: IndicatorConfig, shape: type[C]
) -> C:
    """Every strategy is only ever invoked for its own `shape` (dispatched via
    `SHAPE_REGISTRY`), so this narrowing always succeeds — it exists to give
    basedpyright the concrete `XCalculation` type instead of the `Calculation`
    union.
    """
    if not isinstance(config.calculation, shape):
        raise TypeError(
            f'esperado calculation do shape {shape.__name__}, '
            f'recebido {type(config.calculation).__name__}'
        )
    return config.calculation
