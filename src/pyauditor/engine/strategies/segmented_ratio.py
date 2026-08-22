"""`segmented_ratio` shape: 3 sub-ratios (priority Alta/Média/Baixa), each
against the shared `target`, each with its own `step_points`; penalty is the
sum of the 3. See docs/spec/inms-pipeline.md §2 (INMS 1.2, Anexo D Tabela 28).

`result_pct`/`conforms` on the shared `CalculationResult` have no single
Anexo-D-defined meaning for a 3-category shape — `result_pct` here is the
pooled ratio (sum of all numerators / sum of all denominators) as a headline
figure for the ROM's generic "resultado vs meta" section, and `conforms` is
true only when every category met the target (i.e. total penalty is zero).
The authoritative per-category breakdown is in `memoria["categories"]`.
"""

from math import isclose

from pyauditor.config.models import IndicatorConfig, SegmentedRatioCalculation
from pyauditor.engine.strategies._filters import filter_rows
from pyauditor.engine.strategies._numbers import as_float
from pyauditor.engine.strategies._target import safe_pct, shortfall
from pyauditor.engine.strategies.base import (
    CalculationResult,
    narrow_calculation,
)


class SegmentedRatioStrategy:
    def calculate(
        self, config: IndicatorConfig, rows: list[dict[str, str]]
    ) -> CalculationResult:
        calculation = narrow_calculation(config, SegmentedRatioCalculation)
        if config.target is None:
            raise ValueError('segmented_ratio exige `target`')

        categories: list[dict[str, object]] = []
        total_numerator = 0
        total_denominator = 0
        total_penalty = 0.0

        for category in calculation.categories:
            denominator_rows = filter_rows(rows, category.denominator_filter)
            numerator_rows = filter_rows(
                denominator_rows, category.numerator_filter
            )

            numerator = len(numerator_rows)
            denominator = len(denominator_rows)
            result_pct = safe_pct(numerator, denominator)

            category_shortfall = max(
                shortfall(
                    result_pct, config.target.operator, config.target.value
                ),
                0.0,
            )
            penalty = (
                category_shortfall / calculation.step_size_pct
            ) * category.step_points

            categories.append(
                {
                    'name': category.name,
                    'numerator': numerator,
                    'denominator': denominator,
                    'result_pct': result_pct,
                    'penalty_points': penalty,
                }
            )
            total_numerator += numerator
            total_denominator += denominator
            total_penalty += penalty

        pooled_result_pct = safe_pct(total_numerator, total_denominator)

        return CalculationResult(
            result_pct=pooled_result_pct,
            conforms=isclose(total_penalty, 0.0),
            penalty_points=total_penalty,
            memoria={'categories': categories},
        )

    def pool_numerator_denominator(
        self, memoria: dict[str, object]
    ) -> tuple[float | None, float | None]:
        categories = memoria.get('categories')
        if not isinstance(categories, list):
            return None, None
        numerator = sum(
            as_float(c.get('numerator')) or 0.0
            for c in categories
            if isinstance(c, dict)
        )
        denominator = sum(
            as_float(c.get('denominator')) or 0.0
            for c in categories
            if isinstance(c, dict)
        )
        return numerator, denominator
