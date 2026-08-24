"""Aba INMS_BASE do relatório por órgão (ticket 09 SRP).

Builder e helpers de linha da planilha `INMS_BASE`, extraídos de
`excel/report.py`.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from openpyxl import Workbook

from pyauditor.codes import contractual_sort_key
from pyauditor.excel._style import CellValue, new_sheet, write_row
from pyauditor.excel.groups import group_for_summary
from pyauditor.excel.inms_base import inms_base_fields
from pyauditor.rom.summary import IndicatorSummary

INMS_BASE_SHEET: Final[str] = 'INMS_BASE'

_INMS_BASE_COLUMNS: Final[tuple[str, ...]] = (
    'Competência',
    'Item contratual',
    'Serviço',
    'Grupo operacional',
    'Código INMS',
    'Descrição',
    'Órgão',
    'Meta mínima ou máxima',
    'Sentido da meta',
    'Numerador',
    'Denominador',
    'Resultado calculado',
    'Unidade',
    'Aplicabilidade',
    'Resultado esperado',
    'Conformidade',
    'Diferença para a meta',
    'Ocorrência de glosa',
    'Percentual de glosa',
    'Valor-base',
    'Valor da glosa',
    'Justificativa',
    'Referência da evidência',
    'Número SEI',
    'Responsável pela evidência',
    'Observação do fiscal',
)

_MINIMUM_BODY_ROW: Final[int] = 2


def sort_key(
    summary: IndicatorSummary,
) -> tuple[tuple[int, str, int, str], str]:
    """Return a deterministic contractual and asset ordering key."""
    return (contractual_sort_key(summary.contractual_id), summary.asset or '')


def inms_base_row(
    competencia: str,
    summary: IndicatorSummary,
) -> tuple[CellValue, ...]:
    """Convert a measured summary into an INMS_BASE worksheet row."""
    group = group_for_summary(
        summary.indicator_id,
        summary.contractual_id,
    )
    row = inms_base_fields(summary, competencia, grupo_operacional=group)

    return (
        row.competencia,
        None,
        row.servico,
        row.grupo_operacional,
        row.codigo_inms,
        row.descricao,
        row.orgao,
        row.meta,
        row.sentido,
        row.numerador,
        row.denominador,
        row.resultado,
        row.unidade,
        None,
        None,
        row.conformidade,
        row.diferenca,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
    )


def build_inms_base_sheet(
    workbook: Workbook,
    competencia: str,
    summaries: Sequence[IndicatorSummary],
) -> None:
    """Create and populate the canonical INMS_BASE worksheet."""
    sheet = new_sheet(
        workbook,
        INMS_BASE_SHEET,
        _INMS_BASE_COLUMNS,
        width=20,
    )

    for row_index, summary in enumerate(
        sorted(summaries, key=sort_key),
        start=_MINIMUM_BODY_ROW,
    ):
        write_row(
            sheet,
            row_index,
            inms_base_row(competencia, summary),
        )
