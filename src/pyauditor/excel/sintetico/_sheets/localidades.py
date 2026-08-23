"""Aba "Localidades" de `sintetico.xlsx`: tabela de referência com as
localidades atendidas pelo contrato, lida de `input/localidades.csv`
(`excel/localidades.py`). Mesmo esqueleto visual (título/subtítulo/seção)
das demais abas institucionais — título/subtítulo referenciam `Capa!B2`,
nunca redigitados.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from openpyxl import Workbook

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
from pyauditor.excel.localidades import (
    CATEGORIAS_PRESENCIAL_HEADER,
    CATEGORIAS_REMOTA_HEADER,
    ENDERECO_HEADER,
    LOCALIDADE_HEADER,
    QUANTIDADE_USUARIOS_HEADER,
    read_localidades,
)
from pyauditor.excel.sintetico._sheets._shared import LOCALIDADES_SHEET_NAME

_TITLE: Final[str] = (
    'DEMONSTRATIVO DE EXECUÇÃO DOS SERVIÇOS DE INFRAESTRUTURA DE TI'
)
_SUBTITLE_REF_FORMULA: Final[str] = '=Capa!B2'
_SECTION_TITLE: Final[str] = 'LOCALIDADES ATENDIDAS'

_ROW_TITLE: Final[int] = 1
_ROW_SUBTITLE: Final[int] = 2
_ROW_SECTION: Final[int] = 4
_ROW_HEADER: Final[int] = 6
_ROW_BODY_START: Final[int] = 7

_COLUMN_WIDTHS: Final[tuple[tuple[str, float], ...]] = (
    ('A', 5),
    ('B', 34.0),
    ('C', 46.0),
    ('D', 42.0),
    ('E', 30.0),
    ('F', 16.0),
)

_HEADERS: Final[tuple[tuple[int, str], ...]] = (
    (2, LOCALIDADE_HEADER),
    (3, ENDERECO_HEADER),
    (4, CATEGORIAS_PRESENCIAL_HEADER),
    (5, CATEGORIAS_REMOTA_HEADER),
    (6, QUANTIDADE_USUARIOS_HEADER),
)


def _write_localidades_sheet(
    workbook: Workbook,
    path: Path,
    contract_number: str | None,
    warnings: list[str],
) -> None:
    """Aba "Localidades": título/subtítulo compartilhados com a Capa +
    tabela LOCALIDADE/ENDEREÇO/CATEGORIAS (PRESENCIAL)/CATEGORIAS (REMOTA)/
    QUANTIDADE DE USUÁRIOS, uma linha por localidade de `localidades.csv`."""
    try:
        localidades = read_localidades(path)
    except FileNotFoundError:
        warnings.append(
            f'sintetico.xlsx: {path} não encontrado — aba '
            f"'{LOCALIDADES_SHEET_NAME}' não gerada"
        )
        return
    except (OSError, ValueError) as exc:
        warnings.append(
            f'sintetico.xlsx: falha ao ler {path}: {exc} — aba '
            f"'{LOCALIDADES_SHEET_NAME}' não gerada"
        )
        return

    sheet = workbook.create_sheet(title=LOCALIDADES_SHEET_NAME)
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

    for column, label in _HEADERS:
        cell = sheet.cell(row=_ROW_HEADER, column=column, value=label)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = CENTER_ALIGN if column == 6 else LEFT_WRAP_ALIGN

    row = _ROW_BODY_START
    for index, localidade in enumerate(localidades):
        row_fill = SUBSTITUTO_FILL if index % 2 == 1 else None
        for column, header in _HEADERS:
            value = localidade.get(header, '')
            cell = sheet.cell(row=row, column=column)
            if header == QUANTIDADE_USUARIOS_HEADER:
                try:
                    cell.value = int(value)
                    cell.alignment = CENTER_ALIGN
                except ValueError:
                    cell.value = value
                    cell.alignment = CENTER_ALIGN
            else:
                cell.value = value
                cell.alignment = LEFT_WRAP_ALIGN
            cell.font = BODY_FONT
            cell.border = THIN_BORDER
            if row_fill is not None:
                cell.fill = row_fill
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
