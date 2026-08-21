"""`external_catalog_sum` shape: linear sum of Anexo E catalog points, with
max-points-wins dedup when an occurrence matches multiple catalog items, no
cap or reincidência multiplier. See docs/spec/inms-pipeline.md §2, §11
(INMS 1.8).

Ticket 06 doesn't solve dataset ingestion (still fog — spec §11.3): each row
is assumed to already carry the matched Anexo E code(s) for that occurrence,
not raw ticket data this strategy would have to classify itself.
"""

from pyauditor.config.catalog import load_anexo_e_catalog
from pyauditor.config.models import ExternalCatalogSumCalculation, IndicatorConfig
from pyauditor.engine.strategies.base import (
    CalculationResult,
    narrow_calculation,
    no_pooled_numerator_denominator,
)


class ExternalCatalogSumStrategy:
    def calculate(self, config: IndicatorConfig, rows: list[dict[str, str]]) -> CalculationResult:
        calculation = narrow_calculation(config, ExternalCatalogSumCalculation)
        catalog = load_anexo_e_catalog()

        occurrences: list[dict[str, object]] = []
        total_points = 0

        for row in rows:
            codes_raw = row.get(calculation.catalog_codes_column, "")
            codes = [
                c.strip()
                for c in codes_raw.split(calculation.catalog_codes_separator)
                if c.strip()
            ]
            matched = [catalog[code] for code in codes if code in catalog]
            if not matched:
                continue

            best = max(matched, key=lambda item: item.pontos)
            occurrences.append(
                {
                    "occurrence_id": row.get(calculation.occurrence_id_column, ""),
                    "catalog_id": best.id,
                    "descricao": best.descricao,
                    "pontos": best.pontos,
                }
            )
            total_points += best.pontos

        return CalculationResult(
            result_pct=0.0,  # no percentage meta for this shape
            conforms=total_points == 0,
            penalty_points=float(total_points),
            memoria={"occurrences": occurrences, "total_points": total_points},
        )

    # Point/aggregated measure, not a ratio — no numerator/denominator.
    pool_numerator_denominator = staticmethod(no_pooled_numerator_denominator)
