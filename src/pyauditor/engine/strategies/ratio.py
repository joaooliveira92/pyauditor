"""`ratio` shape: numerator/denominator x 100 against a target, linear penalty.

See docs/spec/inms-pipeline.md §2 and §7.1. All 3 `aggregation` variants are
implemented: `count_distinct` (ticket 02), `sum` and `precomputed` (ticket 07).
"""

from pyauditor.config.models import IndicatorConfig, RatioCalculation
from pyauditor.engine.strategies._filters import filter_rows
from pyauditor.engine.strategies._target import meets_target, safe_pct, shortfall
from pyauditor.engine.strategies.base import CalculationResult, narrow_calculation


class RatioStrategy:
    def calculate(self, config: IndicatorConfig, rows: list[dict[str, str]]) -> CalculationResult:
        calculation = narrow_calculation(config, RatioCalculation)
        assert config.target is not None
        assert config.penalty is not None

        numerator, denominator = _aggregate(calculation, rows)
        result_pct = safe_pct(numerator, denominator)

        if denominator == 0:
            # No eligible activity in the competência (e.g. zero projects/mudanças
            # that month) is not the same as 0% performance — there's nothing to
            # measure against the target, so it can't be penalized as a failure.
            conforms = True
            penalty_points = 0.0
        else:
            conforms = meets_target(result_pct, config.target.operator, config.target.value)
            penalty_points = 0.0 if conforms else _linear_penalty(
                result_pct=result_pct,
                target=config.target.value,
                operator=config.target.operator,
                base_points=config.penalty.base_points,
                step_points=config.penalty.step_points,
                step_size_pct=config.penalty.step_size_pct,
            )

        return CalculationResult(
            result_pct=result_pct,
            conforms=conforms,
            penalty_points=penalty_points,
            memoria={"numerator": numerator, "denominator": denominator},
        )


def _aggregate(calculation: RatioCalculation, rows: list[dict[str, str]]) -> tuple[float, float]:
    if calculation.aggregation == "count_distinct":
        denominator_rows = filter_rows(rows, calculation.denominator_filter)
        numerator_rows = filter_rows(denominator_rows, calculation.numerator_filter)
        return float(len(numerator_rows)), float(len(denominator_rows))

    if calculation.aggregation == "sum":
        assert calculation.sum_numerator_column is not None
        assert calculation.sum_denominator_extra_column is not None
        numerator = sum(
            float(row[calculation.sum_numerator_column]) for row in rows if row.get(calculation.sum_numerator_column)
        )
        extra = sum(
            float(row[calculation.sum_denominator_extra_column])
            for row in rows
            if row.get(calculation.sum_denominator_extra_column)
        )
        return numerator, numerator + extra

    # precomputed: exactly one row per file (one YAML+CSV = one ativo/serviço
    # medição independente — spec §2.1/ticket 13); its value already is the
    # result percentage, so numerator/value, denominator/100 reproduces it
    # unchanged through the same numerator/denominator*100 arithmetic below.
    assert calculation.precomputed_result_column is not None
    assert len(rows) == 1, "aggregation: precomputed espera exatamente 1 linha por CSV"
    return float(rows[0][calculation.precomputed_result_column]), 100.0


def _linear_penalty(
    result_pct: float,
    target: float,
    operator: str,
    base_points: float,
    step_points: float,
    step_size_pct: float,
) -> float:
    steps = max(shortfall(result_pct, operator, target), 0.0) / step_size_pct
    return base_points + steps * step_points
