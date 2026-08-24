"""Abas de grupo operacional do relatório por órgão (ticket 09 SRP).

Builders e helpers de linha das planilhas de grupo (`GROUP_TABS`),
extraídos de `excel/report.py`.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from openpyxl import Workbook

from pyauditor.codes import format_inms_code
from pyauditor.excel._report_inms_base import sort_key
from pyauditor.excel._style import CellValue, new_sheet, write_row
from pyauditor.excel.groups import GROUP_TABS, group_for_summary
from pyauditor.rom.summary import IndicatorSummary

_GROUP_TAB_COLUMNS: Final[tuple[str, ...]] = (
    'Código INMS',
    'Descrição',
    'Serviço',
    'Órgão',
    'Resultado (%)',
    'Meta',
    'Conformidade',
    'Penalidade (pontos)',
)

_MINIMUM_BODY_ROW: Final[int] = 2


def group_row(
    summary: IndicatorSummary,
) -> tuple[CellValue, ...]:
    """Convert a measured summary into an operational group row."""
    return (
        format_inms_code(summary.contractual_id),
        summary.name,
        summary.asset,
        summary.orgao,
        round(summary.result_pct, 2),
        summary.target_value,
        'Conforme' if summary.conforms else 'Não conforme',
        round(summary.penalty_points, 2),
    )


def build_group_sheets(
    workbook: Workbook,
    summaries: Sequence[IndicatorSummary],
) -> None:
    """Create every configured operational group worksheet."""
    summaries_by_group: dict[str, list[IndicatorSummary]] = {
        group: [] for group in GROUP_TABS
    }

    for summary in summaries:
        group = group_for_summary(
            summary.indicator_id,
            summary.contractual_id,
        )
        if group is not None:
            summaries_by_group[group].append(summary)

    for group in GROUP_TABS:
        sheet = new_sheet(
            workbook,
            group,
            _GROUP_TAB_COLUMNS,
            width=22,
        )

        for row_index, summary in enumerate(
            sorted(summaries_by_group[group], key=sort_key),
            start=_MINIMUM_BODY_ROW,
        ):
            write_row(
                sheet,
                row_index,
                group_row(summary),
            )
