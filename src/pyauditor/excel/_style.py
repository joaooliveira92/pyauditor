"""Shared cell styles, per docs/styleguide.md (Arial 10 body, bold dark
headers, thin borders, no decorative fills) — reused by `capa.py` and
`report.py` so both tabs look consistent.
"""

from typing import Final

from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

TITLE_FONT: Final = Font(name="Arial", size=14, bold=True)
LABEL_FONT: Final = Font(name="Arial", size=10, bold=True)
BODY_FONT: Final = Font(name="Arial", size=10)
HEADER_FONT: Final = Font(name="Arial", size=10, bold=True, color="FFFFFF")
HEADER_FILL: Final = PatternFill(start_color="1F2937", end_color="1F2937", fill_type="solid")
BOTTOM_BORDER: Final = Border(bottom=Side(style="thin", color="D1D5DB"))
LEFT_ALIGN: Final = Alignment(horizontal="left")
