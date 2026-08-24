"""Seção 1 (Identificação) — compartilhada entre as abas enriquecidas de
INMS; extraída de `excel/inms_1_1/_sections_1_3.py` quando o INMS 1.2 ganhou
seu próprio renderer enriquecido. O único ponto variável por indicador é o
título (linha 1) — passado explicitamente pelo chamador.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from openpyxl.worksheet.worksheet import Worksheet

from pyauditor.excel._inms_audit_common._cells import (
    CellValue,
    label_value,
    section_bar,
)
from pyauditor.excel._inms_audit_common._layout import (
    DATE_FMT,
    DATETIME_FMT,
    GRAY_FILL,
    TITLE_FONT,
)
from pyauditor.excel._safety import safe_excel_text
from pyauditor.periodo import PeriodoAfericao


def write_section_1_identificacao(
    sheet: Worksheet,
    *,
    title: str,
    rows: list[dict[str, str]],
    contract: str,
    periodo: PeriodoAfericao | None,
    raw_csv_path: Path,
    generated_at: datetime,
) -> None:
    sheet.merge_cells('A1:L1')
    t = sheet.cell(row=1, column=1, value=title)
    t.font = TITLE_FONT

    section_bar(sheet, 3, 'SEÇÃO 1 · IDENTIFICAÇÃO')
    data_corte: CellValue
    if periodo is not None:
        competencia = (
            f'{periodo.inicio:%d/%m/%Y} '
            f'a '
            f'{periodo.fim:%d/%m/%Y} '
            f'({periodo.inicio:%Y-%m})'
        )
        data_corte = periodo.fim
        data_corte_fmt = DATE_FMT
    else:
        competencia = 'Não informado'
        data_corte = 'Não informado'
        data_corte_fmt = None
    label_value(sheet, 4, 'Competência:', competencia, fill=GRAY_FILL)
    label_value(
        sheet, 5, 'Contrato:', safe_excel_text(contract), fill=GRAY_FILL
    )
    label_value(
        sheet,
        6,
        'Fonte dos dados:',
        # Só o nome do arquivo, não o caminho completo — evita expor
        # estrutura de diretório/usuário do ambiente que gerou a planilha
        # (ticket 19 / B-02).
        safe_excel_text(f'{raw_csv_path.name} ({len(rows)} registros brutos)'),
        fill=GRAY_FILL,
    )
    label_value(
        sheet,
        7,
        'Data de geração:',
        generated_at,
        fmt=DATETIME_FMT,
        fill=GRAY_FILL,
    )
    label_value(
        sheet,
        8,
        'Data de corte:',
        data_corte,
        fmt=data_corte_fmt,
        fill=GRAY_FILL,
    )
    label_value(
        sheet,
        9,
        'Responsável pela elaboração:',
        'Não informado',
        fill=GRAY_FILL,
    )
