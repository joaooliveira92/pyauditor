"""Aba "Sansões" de `sintetico.xlsx`: catálogo de desconformidades técnicas
do Anexo E (`configs/anexo_e.yaml`, `config/catalog.py`) — um item por
linha (id/categoria/descrição/referência/pontos). Mesmo esqueleto visual
(título/subtítulo/seção) das demais abas institucionais — título/subtítulo
referenciam `Capa!B2`, nunca redigitados.
"""

from __future__ import annotations

from typing import Final

from openpyxl import Workbook

from pyauditor.config.catalog import load_anexo_e_catalog
from pyauditor.excel._style import (
    BODY_FONT,
    CENTER_ALIGN,
    HEADER_FILL,
    HEADER_FONT,
    LEFT_WRAP_ALIGN,
    SECTION_FONT,
    SUBSTITUTO_FILL,
    SUBTITLE_FONT,
    THIN_BORDER,
    TITLE_FONT,
    setup_institutional_print,
)
from pyauditor.excel.sintetico._sheets._shared import SANCOES_SHEET_NAME

_TITLE: Final[str] = (
    'DEMONSTRATIVO DE EXECUÇÃO DOS SERVIÇOS DE INFRAESTRUTURA DE TI'
)
_SUBTITLE_REF_FORMULA: Final[str] = '=Capa!B2'
_SECTION_TITLE: Final[str] = (
    'ANEXO E — ITENS DE DESCONFORMIDADE TÉCNICA'
)

_ROW_TITLE: Final[int] = 1
_ROW_SUBTITLE: Final[int] = 2
_ROW_SECTION: Final[int] = 4
_ROW_HEADER: Final[int] = 6
_ROW_BODY_START: Final[int] = 7

_COLUMN_WIDTHS: Final[tuple[tuple[str, float], ...]] = (
    ('A', 5),
    ('B', 10.0),
    ('C', 26.0),
    ('D', 62.0),
    ('E', 18.0),
    ('F', 12.0),
)

_HEADERS: Final[tuple[str, ...]] = (
    'ID', 'Categoria', 'Descrição', 'Referência', 'Pontos',
)


def _write_sancoes_sheet(
    workbook: Workbook,
    contract_number: str | None,
    warnings: list[str],
) -> None:
    """Aba "Sansões": título/subtítulo compartilhados com a Capa + tabela
    ID/Categoria/Descrição/Referência/Pontos, uma linha por item do
    catálogo do Anexo E."""
    try:
        catalog = load_anexo_e_catalog()
    except (RuntimeError, ValueError) as exc:
        warnings.append(
            f'sintetico.xlsx: falha ao carregar catálogo do Anexo E: {exc} '
            f"— aba '{SANCOES_SHEET_NAME}' não gerada"
        )
        return

    sheet = workbook.create_sheet(title=SANCOES_SHEET_NAME)
    sheet.sheet_view.showGridLines = False
    for column_letter, width in _COLUMN_WIDTHS:
        sheet.column_dimensions[column_letter].width = width

    sheet.cell(row=_ROW_TITLE, column=2, value=_TITLE).font = TITLE_FONT
    sheet.row_dimensions[_ROW_TITLE].height = 18
    sheet.cell(
        row=_ROW_SUBTITLE, column=2, value=_SUBTITLE_REF_FORMULA
    ).font = SUBTITLE_FONT

    sheet.merge_cells(
        start_row=_ROW_SECTION, start_column=2, end_row=_ROW_SECTION,
        end_column=6,
    )
    sheet.cell(
        row=_ROW_SECTION, column=2, value=_SECTION_TITLE
    ).font = SECTION_FONT
    sheet.row_dimensions[_ROW_SECTION].height = 16

    for offset, label in enumerate(_HEADERS):
        column = 2 + offset
        cell = sheet.cell(row=_ROW_HEADER, column=column, value=label)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = CENTER_ALIGN if column in (2, 6) else LEFT_WRAP_ALIGN

    row = _ROW_BODY_START
    for index, item in enumerate(catalog.values()):
        row_fill = SUBSTITUTO_FILL if index % 2 == 1 else None
        values = (item.id, item.categoria, item.descricao, item.referencia)
        for offset, value in enumerate(values):
            column = 2 + offset
            cell = sheet.cell(row=row, column=column, value=value)
            cell.font = BODY_FONT
            cell.border = THIN_BORDER
            cell.alignment = (
                CENTER_ALIGN if column == 2 else LEFT_WRAP_ALIGN
            )
            if row_fill is not None:
                cell.fill = row_fill

        pontos_cell = sheet.cell(row=row, column=6, value=item.pontos)
        pontos_cell.font = BODY_FONT
        pontos_cell.border = THIN_BORDER
        pontos_cell.alignment = CENTER_ALIGN
        if row_fill is not None:
            pontos_cell.fill = row_fill

        row += 1

    last_row = row - 1
    setup_institutional_print(
        sheet,
        contract_number=contract_number,
        last_row=last_row,
        last_column=6,
        header_row=_ROW_HEADER,
        first_column=2,
    )
