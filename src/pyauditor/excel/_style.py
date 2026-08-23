"""Provide shared styles and worksheet-writing utilities.

The styles defined here follow ``docs/styleguide.md``:

- Arial 10-point font for body cells;
- bold Arial headers with a dark background;
- thin bottom borders for body rows;
- no decorative fills;
- hidden worksheet gridlines.

This module is the canonical source of worksheet styles, shape-to-unit
mappings, and common sheet-writing behavior used by ``capa.py``,
``report.py``, and ``consolidate.py``.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

__all__: Final[tuple[str, ...]] = (
    'BODY_FONT',
    'BOTTOM_BORDER',
    'CENTER_ALIGN',
    'CENTER_WRAP_ALIGN',
    'CRITICIDADE_FILL_BY_VALUE',
    'HEADER_FILL',
    'HEADER_FONT',
    'LABEL_FONT',
    'LEFT_ALIGN',
    'LEFT_WRAP_ALIGN',
    'PENDING_FILL',
    'SECTION_FONT',
    'SUBSTITUTO_FILL',
    'SUBTITLE_FONT',
    'THIN_BORDER',
    'TITLE_FONT',
    'TOP_WRAP_ALIGN',
    'UNIT_BY_SHAPE',
    'CellValue',
    'new_sheet',
    'setup_institutional_print',
    'write_row',
)

TITLE_FONT: Final = Font(name='Arial', size=14, bold=True)
SUBTITLE_FONT: Final = Font(name='Arial', size=11, bold=True)
SECTION_FONT: Final = Font(name='Arial', size=12, bold=True)
LABEL_FONT: Final = Font(name='Arial', size=10, bold=True)
BODY_FONT: Final = Font(name='Arial', size=10)
HEADER_FONT: Final = Font(
    name='Arial',
    size=10,
    bold=True,
    color='FFFFFFFF',
)
HEADER_FILL: Final = PatternFill(
    start_color='FF1F2937',
    end_color='FF1F2937',
    fill_type='solid',
)
BOTTOM_BORDER: Final = Border(
    bottom=Side(style='thin', color='FFD1D5DB'),
)
THIN_BORDER: Final = Border(
    top=Side(style='thin', color='FFD1D5DB'),
    bottom=Side(style='thin', color='FFD1D5DB'),
    left=Side(style='thin', color='FFD1D5DB'),
    right=Side(style='thin', color='FFD1D5DB'),
)
LEFT_ALIGN: Final = Alignment(horizontal='left', vertical='center')
CENTER_ALIGN: Final = Alignment(horizontal='center', vertical='center')
LEFT_WRAP_ALIGN: Final = Alignment(
    horizontal='left', vertical='center', wrap_text=True
)
CENTER_WRAP_ALIGN: Final = Alignment(
    horizontal='center', vertical='center', wrap_text=True
)
TOP_WRAP_ALIGN: Final = Alignment(
    horizontal='left', vertical='top', wrap_text=True
)

# Sinalização de pendência documental (spec de revisão Capa/Equipe/Prazos) —
# amarelo-claro para questões que exigem interpretação/fonte externa, nunca
# corrigidas automaticamente.
PENDING_FILL: Final = PatternFill(
    start_color='FFFFF3CD', end_color='FFFFF3CD', fill_type='solid'
)
# Linhas de substituto na aba Equipe — discreto, não reduz relevância formal.
SUBSTITUTO_FILL: Final = PatternFill(
    start_color='FFF3F4F6', end_color='FFF3F4F6', fill_type='solid'
)
CRITICIDADE_FILL_BY_VALUE: Final[Mapping[str, PatternFill]] = MappingProxyType(
    {
        'Alta': PatternFill(
            start_color='FFF8D7DA', end_color='FFF8D7DA', fill_type='solid'
        ),
        'Média': PatternFill(
            start_color='FFFFF3CD', end_color='FFFFF3CD', fill_type='solid'
        ),
        'Baixa': PatternFill(
            start_color='FFD4EDDA', end_color='FFD4EDDA', fill_type='solid'
        ),
        'Não aplicável': PatternFill(
            start_color='FFE9ECEF', end_color='FFE9ECEF', fill_type='solid'
        ),
    }
)

type CellValue = str | float | int | None

UNIT_BY_SHAPE: Final[Mapping[str, str]] = MappingProxyType(
    {
        'ratio': '%',
        'segmented_ratio': '%',
        'count_difference': 'unidades',
        'external_catalog_sum': 'pontos',
    }
)


def new_sheet(
    workbook: Workbook,
    name: str,
    columns: tuple[str, ...],
    width: int = 24,
) -> Worksheet:
    """Create and initialize a consistently styled worksheet.

    The function modifies ``workbook`` by creating a worksheet, writing its
    headers in the first row, setting a uniform column width, hiding gridlines,
    and freezing the header row.

    Args:
        workbook: Workbook that will own the new worksheet.
        name: Exact worksheet name. It must be non-empty and unique within the
            workbook.
        columns: Non-empty sequence of column headings.
        width: Positive display width applied to every declared column.

    Returns:
        The newly created and initialized worksheet.

    Raises:
        ValueError: If ``name`` is empty, a worksheet with the same name
            already exists, ``columns`` is empty, a heading before the last
            non-empty one is empty, or ``width`` is not positive.

    Note:
        Trailing empty headings are allowed so verbatim reproductions of
        tabular text files (such as the Capa CSV) can keep their exact column
        count even when the file ends a row with an empty cell.
    """
    if not name.strip():
        raise ValueError('Nome da planilha não pode ser vazio.')

    if name in workbook.sheetnames:
        raise ValueError(f'Planilha já existe: {name!r}.')

    if not columns:
        raise ValueError('Planilha deve declarar pelo menos uma coluna.')

    meaningful_columns = list(columns)
    while meaningful_columns and not meaningful_columns[-1].strip():
        meaningful_columns.pop()

    if not meaningful_columns or any(
        not column.strip() for column in meaningful_columns
    ):
        raise ValueError(
            'Cabeçalhos de coluna da planilha não podem ser vazios.'
        )

    if isinstance(width, bool) or width <= 0:
        raise ValueError(
            'Largura de coluna da planilha deve ser um inteiro positivo.'
        )

    sheet: Worksheet = workbook.create_sheet(title=name)
    sheet.sheet_view.showGridLines = False

    for column_index, column_name in enumerate(columns, start=1):
        cell = sheet.cell(row=1, column=column_index, value=column_name)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = LEFT_ALIGN
        sheet.column_dimensions[cell.column_letter].width = width

    sheet.freeze_panes = 'A2'
    return sheet


def write_row(
    sheet: Worksheet,
    row_idx: int,
    values: tuple[CellValue, ...],
    *,
    expected_columns: int | None = None,
) -> None:
    """Write and style one complete worksheet body row.

    By default, the number of values must match the number of columns already
    declared on the worksheet (its header row). Existing cells at ``row_idx``
    are overwritten.

    Args:
        sheet: Worksheet that receives the row.
        row_idx: One-based destination row. Body rows must start after the
            header row.
        values: Cell values in the same order as the worksheet columns.
        expected_columns: Column count to validate ``values`` against, instead
            of the worksheet's declared header width. Needed when a sheet
            carries more than one differently-shaped row block (e.g. a second
            verbatim CSV block appended below the sheet's own header).

    Raises:
        ValueError: If ``row_idx`` refers to the header row or an earlier row,
            or if the number of values differs from the expected column
            count.
    """
    if isinstance(row_idx, bool) or row_idx < 2:
        raise ValueError(
            'Índice de linha do corpo deve ser um inteiro maior que 1.'
        )

    if expected_columns is None:
        expected_columns = sheet.max_column
    if len(values) != expected_columns:
        raise ValueError(
            'Quantidade de valores não confere com o esquema da planilha: '
            f'esperado {expected_columns}, recebido {len(values)}.'
        )

    for column_index, value in enumerate(values, start=1):
        cell = sheet.cell(row=row_idx, column=column_index, value=value)
        cell.font = BODY_FONT
        cell.border = BOTTOM_BORDER


def setup_institutional_print(
    sheet: Worksheet,
    *,
    contract_number: str | None,
    last_row: int,
    last_column: int,
    header_row: int | None = None,
    first_row: int = 1,
    first_column: int = 1,
) -> None:
    """Aplica a configuração de impressão institucional (revisão Capa/
    Equipe/Prazos): área de impressão sobre o conteúdo, uma página de
    largura, centralizado horizontalmente, margens moderadas e rodapé
    discreto com contrato/aba/página. `header_row`, se informado, repete
    aquela linha em páginas subsequentes (ex.: cabeçalho de tabela).
    `first_row`/`first_column` permitem áreas que começam depois de A1 (ex.:
    Capa, cujo conteúdo começa na coluna B — a coluna A é só um recuo
    visual)."""
    sheet.page_setup.orientation = 'portrait'
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0
    page_setup_pr = sheet.sheet_properties.pageSetUpPr
    if page_setup_pr is not None:
        page_setup_pr.fitToPage = True
    sheet.print_options.horizontalCentered = True
    sheet.page_margins.left = 0.5
    sheet.page_margins.right = 0.5
    sheet.page_margins.top = 0.75
    sheet.page_margins.bottom = 0.75

    # Não usar `sheet.cell(row=1, column=last_column).column_letter`: quando
    # a linha 1 tem células mescladas (ex.: título em `A1:F1`), a célula
    # naquela posição pode ser uma `MergedCell`, que não tem esse atributo.
    first_col_letter = get_column_letter(first_column)
    last_col_letter = get_column_letter(last_column)
    sheet.print_area = (
        f'{first_col_letter}{first_row}:{last_col_letter}{last_row}'
    )
    if header_row is not None:
        sheet.print_title_rows = f'{header_row}:{header_row}'

    contract_part = f'Contrato {contract_number} — ' if contract_number else ''
    odd_footer = sheet.oddFooter
    if odd_footer is not None and odd_footer.center is not None:
        odd_footer.center.text = (
            f'{contract_part}{sheet.title} — Página &P de &N'
        )
