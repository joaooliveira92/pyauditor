"""Shared contract every calculation strategy implements."""

from dataclasses import dataclass
from typing import Protocol, TypeVar

from pyauditor.config.models import Calculation, IndicatorConfig


@dataclass(frozen=True)
class CalculationResult:
    result_pct: float
    conforms: bool
    penalty_points: float
    memoria: dict[str, object]  # shape-specific values the ROM renderer needs


class CalculationStrategy(Protocol):
    def calculate(self, config: IndicatorConfig, rows: list[dict[str, str]]) -> CalculationResult: ...

    def pool_numerator_denominator(
        self, memoria: dict[str, object]
    ) -> tuple[float | None, float | None]:
        """Extracts a headline numerator/denominator from this shape's own
        `memoria` (the ROM/summary layer's pooling question, answered by the
        shape that produced the data — a single source of truth instead of a
        second shape-keyed dispatch living in `rom/summary.py`)."""
        ...


def no_pooled_numerator_denominator(_memoria: dict[str, object]) -> tuple[None, None]:
    """Shared no-op for shapes with no ratio-style numerator/denominator at
    the indicator level (point/aggregated measures)."""
    return None, None


_C = TypeVar("_C", bound=Calculation)


def narrow_calculation(config: IndicatorConfig, shape: type[_C]) -> _C:
    """Every strategy is only ever invoked for its own `shape` (dispatched via
    `SHAPE_REGISTRY`), so this narrowing always succeeds — it exists to give
    mypy the concrete `XCalculation` type instead of the `Calculation` union.
    """
    assert isinstance(config.calculation, shape)
    return config.calculation
