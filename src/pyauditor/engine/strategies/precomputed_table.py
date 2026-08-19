"""`precomputed_table` shape: reads one aggregated "apuração" table per
competência — one row per ativo/serviço/unidade/domínio, each already carrying
the computed result and, typically, the fiscal penalty.

Each row holds the ativo's computed result (`result_column`, percentage or a
point total). The per-ativo penalty is read from `penalty_column` when given
(these datasets are the fiscal apuração sheets, whose penalty formula varies
per indicator — per-point, per-unit, per-control), otherwise it is recomputed
from the config's `target` + `penalty`. Penalties are summed; a single
headline `result_pct` is reported per indicator.

`result_is_percent` (default true):
- ``true`` — per-ativo value is a percentage; headline is the hours-weighted
  pooled result (sum(numerador)/sum(base)*100) when the weighting columns are
  given, else the arithmetic mean of the per-ativo percentages.
- ``false`` — per-ativo value is a point total (e.g. INMS 1.8's PDT sum);
  headline is 0.0.
"""

from math import isnan

from pyauditor.config.models import IndicatorConfig, PrecomputedTableCalculation
from pyauditor.engine.strategies._numbers import parse_decimal
from pyauditor.engine.strategies._target import safe_pct, shortfall
from pyauditor.engine.strategies.base import CalculationResult, narrow_calculation


class PrecomputedTableStrategy:
    def calculate(self, config: IndicatorConfig, rows: list[dict[str, str]]) -> CalculationResult:
        calculation = narrow_calculation(config, PrecomputedTableCalculation)
        assert config.target is not None

        weighted = calculation.numerator_column is not None and calculation.denominator_column is not None
        numerator_sum = 0.0
        denominator_sum = 0.0
        percents: list[float] = []
        categories: list[dict[str, object]] = []
        total_penalty = 0.0

        for row in rows:
            raw_value = row.get(calculation.result_column, "")
            if not raw_value.strip():
                continue  # empty/placeholder rows (trailing ';' garbage) carry no measurement
            value = parse_decimal(raw_value)
            if isnan(value):
                continue

            name = row.get(calculation.name_column, "") if calculation.name_column else ""
            result_pct = value if calculation.result_is_percent else 0.0

            if calculation.penalty_column is not None:
                penalty = parse_decimal(row.get(calculation.penalty_column, "") or "")
                if isnan(penalty):
                    penalty = 0.0
            elif calculation.result_is_percent:
                assert config.penalty is not None
                gap = max(
                    shortfall(value, config.target.operator, config.target.value), 0.0
                )
                penalty = (gap / config.penalty.step_size_pct) * config.penalty.step_points
            else:
                penalty = max(value - config.target.value, 0.0)

            categories.append(
                {"name": name, "result_pct": result_pct, "penalty_points": penalty}
            )
            percents.append(result_pct)
            total_penalty += penalty

            if calculation.numerator_column is not None and calculation.denominator_column is not None:
                numerador = parse_decimal(row.get(calculation.numerator_column, "") or "")
                base = parse_decimal(row.get(calculation.denominator_column, "") or "")
                if not isnan(numerador) and not isnan(base):
                    numerator_sum += numerador
                    denominator_sum += base

        if calculation.result_is_percent and weighted and denominator_sum > 0:
            headline = safe_pct(numerator_sum, denominator_sum)
        elif calculation.result_is_percent and percents:
            headline = sum(percents) / len(percents)
        else:
            headline = 0.0

        return CalculationResult(
            result_pct=headline,
            conforms=total_penalty == 0.0,
            penalty_points=total_penalty,
            memoria={"categories": categories},
        )
