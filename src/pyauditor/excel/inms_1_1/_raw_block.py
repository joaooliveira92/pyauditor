"""Base de apoio R–AQ da aba INMS 1.1 (dados brutos + fórmulas) — o núcleo
compartilhado com outras abas enriquecidas (INMS 1.2) vive em
`excel/_inms_audit_common/_raw_block.py`; este módulo só acrescenta a
extensão específica do INMS 1.1 (controle contratual bruto de N horas
corridas — colunas AB/AC/AE/AI), que não se aplica a indicadores com prazo
variável por linha (ex. INMS 1.2, por SLA).
"""

from __future__ import annotations

from openpyxl.utils import get_column_letter as cl
from openpyxl.worksheet.worksheet import Worksheet

from pyauditor.excel._datetime import PRAZO_TOLERANCIA_MINUTOS
from pyauditor.excel._inms_audit_common._layout import (
    AB,
    AC,
    AE,
    AI,
    BODY_FONT,
    DATETIME_FMT,
    HEADER_FILL,
    HEADER_FONT,
    U,
    V,
    W,
)
from pyauditor.excel._inms_audit_common._raw_block import (
    write_raw_block_core,
)
from pyauditor.excel.inms_1_1._layout import _PRAZO_HORAS_CORRIDAS


def _write_raw_block(
    sheet: Worksheet,
    rows: list[dict[str, str]],
    grupo_rows: list[tuple[str, str, str]],
    last_row: int,
    *,
    first_group_row: int,
) -> None:
    write_raw_block_core(
        sheet, rows, grupo_rows, last_row, first_group_row=first_group_row
    )
    _write_raw_block_brute_contratual(sheet, rows)


def _write_raw_block_brute_contratual(
    sheet: Worksheet, rows: list[dict[str, str]]
) -> None:
    for col, text in {
        AB: 'Limite contratual (abertura + prazo corrido)',
        AC: 'Limite ITSM superior ao contratual bruto',
        AE: 'No prazo (controle contratual bruto)',
        AI: 'Ordem — limite ITSM superior ao contratual bruto',
    }.items():
        cell = sheet.cell(row=1, column=col, value=text)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        sheet.column_dimensions[cl(col)].width = 16

    for i in range(2, len(rows) + 2):
        uc, vc, wc, abc = (
            f'{cl(U)}{i}',
            f'{cl(V)}{i}',
            f'{cl(W)}{i}',
            f'{cl(AB)}{i}',
        )
        ab_cell = sheet.cell(
            row=i,
            column=AB,
            value=f'=IF({uc}="","",{uc}+{_PRAZO_HORAS_CORRIDAS}/24)',
        )
        ab_cell.number_format = DATETIME_FMT
        ac_cell = sheet.cell(
            row=i,
            column=AC,
            value=(
                f'=IF(OR({uc}="",{vc}=""),"Requer análise",'
                f'IF({vc}>{abc}+{PRAZO_TOLERANCIA_MINUTOS}/1440,"Sim","Não"))'
            ),
        )
        ae_cell = sheet.cell(
            row=i,
            column=AE,
            value=f'=IF(OR({wc}="",{abc}=""),"",IF({wc}<={abc},"S","N"))',
        )
        for c in (ab_cell, ac_cell, ae_cell):
            c.font = BODY_FONT

        acc = f'{cl(AC)}{i}'
        ai_cell = sheet.cell(
            row=i,
            column=AI,
            value=f'=IF({acc}="Sim",COUNTIF($AC$2:{acc},"Sim"),"")',
        )
        ai_cell.font = BODY_FONT
