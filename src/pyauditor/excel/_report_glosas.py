"""Aba GLOSAS do relatório por órgão (ticket 09 SRP).

Builder da planilha `GLOSAS`, extraído de `excel/report.py`. A computação
monetária fica no módulo puro `_relatorio_glosa`; aqui só o render.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from openpyxl import Workbook

from pyauditor.excel._relatorio_glosa import (
    compute_report_glosa,
    saldo_anterior_pct_de,
)
from pyauditor.excel._style import new_sheet, write_row
from pyauditor.excel.glosas import Historico, houve_reincidencia
from pyauditor.rom.summary import IndicatorSummary

GLOSAS_SHEET: Final[str] = 'GLOSAS'

_GLOSAS_COLUMNS: Final[tuple[str, ...]] = (
    'Competência',
    'Σ Pontos_NMS do mês',
    'Saldo recebido do mês anterior (p.p.)',
    'Percentual de ajuste',
    'Valor-base',
    'Valor da glosa',
    'Teto atingido?',
    'Saldo rolado para o mês seguinte (p.p.)',
    'Reincidência (3x/6m)?',
)

_MINIMUM_BODY_ROW: Final[int] = 2


def build_glosas_sheet(
    workbook: Workbook,
    competencia: str,
    summaries: Sequence[IndicatorSummary],
    valor_base: float | None,
    *,
    is_final_month: bool,
    historico: Historico,
) -> None:
    """Create the monthly financial adjustment worksheet."""
    sheet = new_sheet(
        workbook,
        GLOSAS_SHEET,
        _GLOSAS_COLUMNS,
        width=26,
    )

    previous_balance = saldo_anterior_pct_de(
        historico,
        competencia,
    )
    glosa = compute_report_glosa(
        competencia,
        summaries,
        valor_base,
        is_final_month=is_final_month,
        historico=historico,
    )
    reincidencia = houve_reincidencia(
        historico,
        competencia,
        glosa.teto_atingido,
    )

    write_row(
        sheet,
        _MINIMUM_BODY_ROW,
        (
            competencia,
            round(glosa.total_points, 2),
            round(previous_balance, 5) if previous_balance else None,
            round(glosa.percentual_ajuste, 5),
            glosa.valor_base,
            (
                round(glosa.valor_da_glosa, 2)
                if glosa.valor_da_glosa is not None
                else None
            ),
            'S' if glosa.teto_atingido else 'N',
            (
                round(glosa.saldo_rolado_pct, 5)
                if glosa.saldo_rolado_pct
                else None
            ),
            'S' if reincidencia else 'N',
        ),
    )
