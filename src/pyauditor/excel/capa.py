"""Builds the contract's Excel capa workbook (`CAPA_E_CONTROLE` tab),
per docs/spreadsheet.md §Aba 1. Idempotent: `bootstrap_capa` never touches a
file that already exists.
"""

from pathlib import Path
from typing import Final

from openpyxl import Workbook, load_workbook
from openpyxl.worksheet.datavalidation import DataValidation

from pyauditor.excel._style import (
    BODY_FONT,
    BOTTOM_BORDER,
    HEADER_FILL,
    HEADER_FONT,
    LABEL_FONT,
    LEFT_ALIGN,
    TITLE_FONT,
)

SHEET_NAME: Final = "CAPA_E_CONTROLE"

# docs/spreadsheet.md §Aba 1 — "Campos"
FIELD_LABELS: Final[tuple[str, ...]] = (
    "Número do contrato",
    "Processo SEI",
    "Empresa contratada",
    "CNPJ da contratada",
    "Órgão contratante atual",
    "Competência",
    "Período inicial da aferição",
    "Período final da aferição",
    "Número da Ordem de Serviço",
    "Número da nota fiscal",
    "Data de emissão da nota fiscal",
    "Fiscal técnico",
    "Fiscal requisitante",
    "Fiscal administrativo",
    "Gestor do contrato",
    "Valor mensal vigente",
    "Versão da planilha",
    "Data da análise",
    "Situação geral da aferição",
)

# docs/spreadsheet.md §Aba 1 — "Situações possíveis"
SITUACOES: Final[tuple[str, ...]] = (
    "Em preenchimento",
    "Aguardando evidências",
    "Em análise",
    "Conforme",
    "Conforme com glosa",
    "Não conforme",
    "Aprovado para pagamento",
    "Não recomendado para pagamento",
)

def build_capa_workbook() -> Workbook:
    """Builds the capa workbook in memory — pure, no filesystem access."""
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.title = SHEET_NAME
    sheet.sheet_view.showGridLines = False

    sheet["A1"] = "Capa e controle do contrato"
    sheet["A1"].font = TITLE_FONT
    sheet.merge_cells("A1:B1")

    sheet["A3"] = "Campo"
    sheet["B3"] = "Valor"
    for cell in (sheet["A3"], sheet["B3"]):
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = LEFT_ALIGN

    situacao_row: int | None = None
    for offset, label in enumerate(FIELD_LABELS):
        row = 4 + offset
        label_cell = sheet.cell(row=row, column=1, value=label)
        label_cell.font = LABEL_FONT
        label_cell.alignment = LEFT_ALIGN
        label_cell.border = BOTTOM_BORDER

        value_cell = sheet.cell(row=row, column=2)
        value_cell.font = BODY_FONT
        value_cell.border = BOTTOM_BORDER
        if label == "Situação geral da aferição":
            value_cell.value = SITUACOES[0]
            situacao_row = row

    if situacao_row is not None:
        validation = DataValidation(
            type="list",
            formula1=f'"{",".join(SITUACOES)}"',
            allow_blank=False,
        )
        sheet.add_data_validation(validation)
        validation.add(sheet.cell(row=situacao_row, column=2))

    sheet.column_dimensions["A"].width = 32
    sheet.column_dimensions["B"].width = 40

    return workbook


def bootstrap_capa(path: Path) -> bool:
    """Creates the capa workbook at `path` if it doesn't exist yet.

    Returns True if the file was created, False if it already existed
    (in which case nothing is touched — bootstrap is idempotent).
    """
    if path.exists():
        return False

    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = build_capa_workbook()
    workbook.save(path)
    return True


def read_valor_mensal_vigente(path: Path) -> float | None:
    """Reads "Valor mensal vigente" from an existing capa — the fiscal
    técnico fills this in by hand after `bootstrap` creates the blank cell,
    so it's None until they do. Used by `report`'s GLOSAS calculation as
    `valor-base` (spec §12.2).
    """
    workbook = load_workbook(path, data_only=True)
    if SHEET_NAME not in workbook.sheetnames:
        return None
    sheet = workbook[SHEET_NAME]

    for row in range(4, 4 + len(FIELD_LABELS)):
        if sheet.cell(row=row, column=1).value == "Valor mensal vigente":
            value = sheet.cell(row=row, column=2).value
            return float(value) if isinstance(value, int | float) else None
    return None
