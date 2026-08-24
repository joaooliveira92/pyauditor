"""Glosa do relatório por órgão (ticket 04 SRP) — aritmética pura, **sem**
`openpyxl` nem builder de workbook.

Extraído de `excel/report.py`: `compute_report_glosa` e o saldo rolado da
competência anterior vivem aqui e são consumidos por `report.py` (aba
`GLOSAS`) e por `cli/report.py` (exit code/publicação). Nenhuma célula nasce
neste módulo.
"""

from __future__ import annotations

from collections.abc import Sequence

from pyauditor.excel.glosas import (
    GlosaResult,
    Historico,
    compute_glosa,
    saldo_anterior_pct_de,
)
from pyauditor.rom.dedup import deduplicate_summaries
from pyauditor.rom.summary import IndicatorSummary

__all__: tuple[str, ...] = (
    'compute_report_glosa',
    'saldo_anterior_pct_de',
)


def _select_glosa_summaries(
    summaries: Sequence[IndicatorSummary],
) -> list[IndicatorSummary]:
    """Select summaries that contribute to the monthly glosa (dedup
    compartilhado — ``rom.dedup.deduplicate_summaries``, ticket 07)."""
    return deduplicate_summaries(summaries)


def compute_report_glosa(
    competencia: str,
    summaries: Sequence[IndicatorSummary],
    valor_base: float | None,
    *,
    is_final_month: bool = False,
    historico: Historico | None = None,
) -> GlosaResult:
    """Compute the monthly glosa rendered by the report.

    Base summaries are excluded when category-derived summaries exist for the
    same contractual indicator and asset. The derived category penalties are
    then summed exactly once.

    Historical state supplies the percentage-point balance rolled over from
    the previous reporting period. Reincidence is not part of the returned
    calculation because it is a reporting flag evaluated separately.

    Args:
        competencia: Reporting period used to resolve historical rollover.
        summaries: Measured indicator summaries for one organization.
        valor_base: Monetary base used to calculate the glosa, when available.
        is_final_month: Whether rollover must follow final-month rules.
        historico: Previously persisted glosa history. Missing history is
            treated as empty.

    Returns:
        The calculated monthly glosa and rollover state.

    Raises:
        ValueError: Propagates invalid financial inputs or reporting periods
            rejected by the glosa domain functions.
    """
    effective_history = historico if historico is not None else {}
    selected_summaries = _select_glosa_summaries(summaries)
    total_points = sum(summary.penalty_points for summary in selected_summaries)
    previous_balance = saldo_anterior_pct_de(
        effective_history,
        competencia,
    )

    return compute_glosa(
        total_points,
        valor_base,
        is_final_month=is_final_month,
        saldo_anterior_pct=previous_balance,
    )
