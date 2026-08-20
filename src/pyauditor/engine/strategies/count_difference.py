"""`count_difference` shape: `CNI = QRC - QCSI`, a count difference (not a
ratio), fixed penalty per missing unit. See docs/spec/inms-pipeline.md §2
(INMS 1.10, Anexo D Tabela 28: meta "= 100%", 1000 pontos por controle não
implementado).

No target/degrau logic applies here — `target` is still consulted for the
ROM's generic "resultado vs meta" section (Anexo D states the meta as
"= 100%", i.e. `result_pct` — implementados/recomendados — must reach the
target), but the penalty itself is `CNI * penalty_per_unit`, not derived from
`target`.
"""

from pyauditor.config.models import CountDifferenceCalculation, IndicatorConfig
from pyauditor.engine.strategies._filters import filter_rows
from pyauditor.engine.strategies._numbers import as_float
from pyauditor.engine.strategies.base import CalculationResult, narrow_calculation


class CountDifferenceStrategy:
    def calculate(self, config: IndicatorConfig, rows: list[dict[str, str]]) -> CalculationResult:
        calculation = narrow_calculation(config, CountDifferenceCalculation)

        recommended_rows = filter_rows(rows, calculation.recommended_filter)
        implemented_rows = filter_rows(recommended_rows, calculation.implemented_filter)

        qrc = len(recommended_rows)
        qcsi = len(implemented_rows)
        cni = qrc - qcsi

        result_pct = (qcsi / qrc) * 100 if qrc else 100.0
        conforms = cni <= 0
        penalty_points = max(cni, 0) * calculation.penalty_per_unit

        return CalculationResult(
            result_pct=result_pct,
            conforms=conforms,
            penalty_points=penalty_points,
            memoria={"QRC": qrc, "QCSI": qcsi, "CNI": cni},
        )

    def pool_numerator_denominator(
        self, memoria: dict[str, object]
    ) -> tuple[float | None, float | None]:
        # Preserves the pooling convention already established in rom/summary.py:
        # (QCSI, QRC) -> (numerator, denominator), not (QRC, QCSI).
        return as_float(memoria.get("QCSI")), as_float(memoria.get("QRC"))
