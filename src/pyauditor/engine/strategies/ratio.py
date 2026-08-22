"""`ratio` shape: numerator/denominator x 100 against a target, linear penalty.

See docs/spec/inms-pipeline.md §2 and §7.1. All 3 `aggregation` variants are
implemented: `count_distinct` (ticket 02), `sum` and `precomputed` (ticket 07).
"""

from math import isnan

from pyauditor.config.models import IndicatorConfig, RatioCalculation
from pyauditor.engine.strategies._filters import filter_rows
from pyauditor.engine.strategies._numbers import as_float, parse_decimal
from pyauditor.engine.strategies._target import (
    meets_target,
    safe_pct,
    shortfall,
)
from pyauditor.engine.strategies.base import (
    CalculationResult,
    narrow_calculation,
)


def _sum_column(rows: list[dict[str, str]], column: str) -> float:
    total = 0.0
    for row in rows:
        raw = row.get(column)
        if not raw:
            continue
        value = parse_decimal(raw)
        if not isnan(value):
            total += value
    return total


class RatioStrategy:
    def calculate(
        self, config: IndicatorConfig, rows: list[dict[str, str]]
    ) -> CalculationResult:
        calculation = narrow_calculation(config, RatioCalculation)
        if config.target is None or config.penalty is None:
            raise ValueError('ratio exige `target` e `penalty` no calculation')

        numerator, denominator = _aggregate(calculation, rows)
        result_pct = safe_pct(numerator, denominator)

        if denominator == 0:
            # No eligible activity in the competência (e.g. zero
            # projects/mudanças
            # that month) is not the same as 0% performance — there's nothing to
            # measure against the target, so it can't be penalized as a failure.
            conforms = True
            penalty_points = 0.0
        else:
            conforms = meets_target(
                result_pct, config.target.operator, config.target.value
            )
            penalty_points = (
                0.0
                if conforms
                else _linear_penalty(
                    result_pct=result_pct,
                    target=config.target.value,
                    operator=config.target.operator,
                    base_points=config.penalty.base_points,
                    step_points=config.penalty.step_points,
                    step_size_pct=config.penalty.step_size_pct,
                )
            )

        return CalculationResult(
            result_pct=result_pct,
            conforms=conforms,
            penalty_points=penalty_points,
            memoria={'numerator': numerator, 'denominator': denominator},
        )

    def pool_numerator_denominator(
        self, memoria: dict[str, object]
    ) -> tuple[float | None, float | None]:
        return as_float(memoria.get('numerator')), as_float(
            memoria.get('denominator')
        )


def _aggregate(
    calculation: RatioCalculation, rows: list[dict[str, str]]
) -> tuple[float, float]:
    if calculation.aggregation == 'count_distinct':
        denominator_rows = filter_rows(rows, calculation.denominator_filter)
        numerator_rows = filter_rows(
            denominator_rows, calculation.numerator_filter
        )
        return float(len(numerator_rows)), float(len(denominator_rows))

    if calculation.aggregation == 'sum':
        if calculation.sum_numerator_column is None:
            raise ValueError('aggregation sum exige `sum_numerator_column`')
        # `denominator_filter` (otherwise count_distinct-only) doubles as the
        # eligible-rows filter here — e.g. INMS 1.6's data ships a "TOTAIS"
        # summary row alongside per-agreement rows; selecting only that row
        # avoids double-counting the per-agreement breakdown underneath it.
        eligible_rows = filter_rows(rows, calculation.denominator_filter)
        raw = _sum_column(eligible_rows, calculation.sum_numerator_column)
        if calculation.sum_denominator_extra_column is not None:
            extra = _sum_column(
                eligible_rows, calculation.sum_denominator_extra_column
            )
            return raw, raw + extra

        if calculation.sum_numerator_subtract_column is None:
            raise ValueError(
                'aggregation sum com subtract exige '
                '`sum_numerator_subtract_column`'
            )
        subtract = _sum_column(
            eligible_rows, calculation.sum_numerator_subtract_column
        )
        return raw - subtract, raw

    # precomputed: exactly one row per file (one YAML+CSV = one ativo/serviço
    # medição independente — spec §2.1/ticket 13); its value already is the
    # result percentage, so numerator/value, denominator/100 reproduces it
    # unchanged through the same numerator/denominator*100 arithmetic below.
    if calculation.precomputed_result_column is None:
        raise ValueError(
            'aggregation precomputed exige `precomputed_result_column`'
        )
    if len(rows) != 1:
        raise ValueError(
            'aggregation: precomputed espera exatamente 1 linha por CSV'
        )
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
