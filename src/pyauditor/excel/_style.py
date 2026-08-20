"""Shared cell styles, per docs/styleguide.md (Arial 10 body, bold dark
headers, thin borders, no decorative fills) — reused by `capa.py`,
`report.py` and `consolidate.py` so every tab looks consistent, plus the
sheet/row-writing helpers and shape→unit vocabulary those two also shared
byte-for-byte until this module became the one place to keep it.
"""

from typing import Final

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.worksheet import Worksheet

TITLE_FONT: Final = Font(name="Arial", size=14, bold=True)
LABEL_FONT: Final = Font(name="Arial", size=10, bold=True)
BODY_FONT: Final = Font(name="Arial", size=10)
HEADER_FONT: Final = Font(name="Arial", size=10, bold=True, color="FFFFFF")
HEADER_FILL: Final = PatternFill(start_color="1F2937", end_color="1F2937", fill_type="solid")
BOTTOM_BORDER: Final = Border(bottom=Side(style="thin", color="D1D5DB"))
LEFT_ALIGN: Final = Alignment(horizontal="left")

CellValue = str | float | int | None

# Shape → display unit for "Unidade" columns (INMS_BASE et al.).
UNIT_BY_SHAPE: Final[dict[str, str]] = {
    "ratio": "%",
    "segmented_ratio": "%",
    "count_difference": "unidades",
    "external_catalog_sum": "pontos",
}


def new_sheet(
    workbook: Workbook, name: str, columns: tuple[str, ...], width: int = 24
) -> Worksheet:
    sheet: Worksheet = workbook.create_sheet(name)
    sheet.sheet_view.showGridLines = False
    for col_idx, column in enumerate(columns, start=1):
        cell = sheet.cell(row=1, column=col_idx, value=column)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = LEFT_ALIGN
        sheet.column_dimensions[cell.column_letter].width = width
    sheet.freeze_panes = "A2"
    return sheet


def write_row(sheet: Worksheet, row_idx: int, values: tuple[CellValue, ...]) -> None:
    for col_idx, value in enumerate(values, start=1):
        cell = sheet.cell(row=row_idx, column=col_idx, value=value)
        cell.font = BODY_FONT
        cell.border = BOTTOM_BORDER
