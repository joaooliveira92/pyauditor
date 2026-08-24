"""Renderer enriquecido de abas precomputed por-ativo (INMS 1.4) del
`sintetico` — reconstruido con el patrón de auditoría de las abas INMS
1.1/1.2/1.3 (ticket 04 SRP).

A diferencia del renderer precomputed plano (`precomputed.py`), esta variante
emite secciones de auditoría que la referencia INMS 1.1 sí tiene:

- **Sección 1** · Identificación (competencia, contrato, fuente, fechas).
- **Sección 2** · Tabla por sistema/servicio con el **resultado a 4 decimales**
  (no 1, que redondeaba 99,451 % → "99,5 %" y lo hacía chocar con la meta),
  meta, desvío en p.p., faixas de 0,1 % y penalidad.
- **Sección 3** · Memoria de cálculo de la penalidad por fila.
- Nota de dominio: NOC/SOC es Nivel único N3 — este indicador no tiene N1 ni
  N2, así que no se replica la Sección 5 (subtotales por nivel) del INMS 1.1.
"""

from __future__ import annotations

from datetime import datetime
from math import isnan
from pathlib import Path
from typing import Final

from openpyxl import Workbook
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter as cl
from openpyxl.worksheet.worksheet import Worksheet

from pyauditor.config.categorias import CategoriasFile, WholeIndicatorMode
from pyauditor.config.models import PrecomputedTableCalculation
from pyauditor.engine.strategies import meets_target, parse_decimal
from pyauditor.excel._inms_audit_common._cells import header_row, section_bar
from pyauditor.excel._inms_audit_common._layout import (
    BODY_FONT,
    LABEL_FONT,
    NOTE_FONT,
    ORANGE_FILL,
    PCT4,
)
from pyauditor.excel._inms_audit_common._section_1 import (
    write_section_1_identificacao,
)
from pyauditor.excel._safety import safe_excel_text
from pyauditor.excel.sintetico._sheets._shared import _NIVEL_BY_CATEGORIA
from pyauditor.periodo import PeriodoAfericao

__all__ = ('_write_precomputed_audit_sheet',)

_SECTION_2_COLUMNS: Final[tuple[str, ...]] = (
    'Categoria',
    'Sistema / Servicio',
    'Resultado',
    'Meta',
    'Desvío vs Meta',
    'Faixas 0,1%',
    'Penalidad',
    'Meta atingida?',
)
# Índices 1-based dentro de `_SECTION_2_COLUMNS` cuyo contenido es numérico.
_NUMERIC_COLS: Final[frozenset[int]] = frozenset({3, 4, 5, 6, 7})

# Anexo D (docs/spreadsheet.md): NOC/SOC penaliza cada 0,1 p.p. — el paso no
# vive en la config precomputed (solo la penalidad final por ativo en
# `penalty_column`), así que se declara aquí para la memoria de la Sección 3.
_STEP_PCT: Final[float] = 0.1

_COLUMN_WIDTHS: Final[dict[int, int]] = {
    1: 28,
    2: 34,
    3: 14,
    4: 12,
    5: 14,
    6: 12,
    7: 12,
    8: 16,
}


def _write_table(
    sheet: Worksheet,
    start_row: int,
    categorias: CategoriasFile,
    entries: list[tuple[str, WholeIndicatorMode]],
    calculation: PrecomputedTableCalculation,
    target_operator: str,
    target_value: float,
    rows: list[dict[str, str]],
) -> int:
    """Escribe la tabla por sistema/servicio. Devuelve la primera fila libre.

    Cada fila guarda `resultado` y `meta` como fracción real (formato PCT4) y
    las derivadas (desvío, faixas) como fórmulas que referencian la misma
    fila, para auditoría viva en la planilla."""
    section_bar(sheet, start_row, 'SEÇÃO 2 · DETALLE POR SISTEMA/SERVICIO')
    header_row(
        sheet, start_row + 1, _SECTION_2_COLUMNS, numeric_cols=_NUMERIC_COLS
    )
    row = start_row + 2
    for categoria_key, _entry in entries:
        categoria = categorias.categorias[categoria_key]
        for data_row in rows:
            raw_value = data_row.get(calculation.result_column, '')
            if not raw_value.strip():
                continue
            value = parse_decimal(raw_value)
            if isnan(value):
                continue

            name = (
                data_row.get(calculation.name_column, '')
                if calculation.name_column
                else ''
            )
            penalidade_raw = (
                data_row.get(calculation.penalty_column, '')
                if calculation.penalty_column
                else ''
            )
            penalidade = (
                parse_decimal(penalidade_raw) if penalidade_raw.strip() else 0.0
            )
            if isnan(penalidade):
                penalidade = 0.0
            atingido = meets_target(value, target_operator, target_value)

            cell_cat = sheet.cell(row=row, column=1, value=categoria.label)
            cell_cat.font = BODY_FONT
            cell_name = sheet.cell(
                row=row, column=2, value=safe_excel_text(name)
            )
            cell_name.font = BODY_FONT
            cell_res = sheet.cell(row=row, column=3, value=value / 100)
            cell_res.number_format = PCT4
            cell_meta = sheet.cell(row=row, column=4, value=target_value / 100)
            cell_meta.number_format = PCT4
            # Desvio vs Meta (Meta - Resultado), positivo cuando queda bajo.
            cell_dev = sheet.cell(row=row, column=5, value=f'=D{row}-C{row}')
            cell_dev.number_format = PCT4
            sheet.cell(
                row=row,
                column=6,
                value=(f'=IF(E{row}<=0,0,ROUNDUP(E{row}*100/{_STEP_PCT:g},0))'),
            ).number_format = '0'
            sheet.cell(row=row, column=7, value=penalidade).number_format = '0'
            sheet.cell(row=row, column=8, value='Sim' if atingido else 'Não')
            row += 1
    return row


def _write_memoria_penalidad(
    sheet: Worksheet,
    start_row: int,
    categorias: CategoriasFile,
    entries: list[tuple[str, WholeIndicatorMode]],
    calculation: PrecomputedTableCalculation,
    target_operator: str,
    target_value: float,
    rows: list[dict[str, str]],
    data_start: int,
) -> None:
    """Sección 3 — memoria de penalidad por fila (referencia las fórmulas de
    la Sección 2)."""
    section_bar(sheet, start_row, 'SEÇÃO 3 · MEMORIA DE LA PENALIDAD')
    row = start_row + 1
    row_idx = data_start
    for _categoria, _entry in entries:
        for data_row in rows:
            raw_value = data_row.get(calculation.result_column, '')
            if not raw_value.strip():
                continue
            value = parse_decimal(raw_value)
            if isnan(value):
                continue
            penalidade_raw = (
                data_row.get(calculation.penalty_column, '')
                if calculation.penalty_column
                else ''
            )
            penalidade = (
                parse_decimal(penalidade_raw) if penalidade_raw.strip() else 0.0
            )
            if isnan(penalidade):
                penalidade = 0.0
            atingido = meets_target(value, target_operator, target_value)

            name = (
                data_row.get(calculation.name_column, '')
                if calculation.name_column
                else ''
            )
            label = safe_excel_text(name) if name else f'Activo {row_idx}'
            head = sheet.cell(
                row=row, column=1, value=f'{label} (fila {row_idx})'
            )
            head.font = LABEL_FONT

            sheet.cell(row=row + 1, column=1, value='Meta:').font = BODY_FONT
            cell = sheet.cell(row=row + 1, column=2, value=target_value / 100)
            cell.number_format = PCT4
            sheet.cell(
                row=row + 1, column=3, value='Resultado:'
            ).font = BODY_FONT
            cell = sheet.cell(row=row + 1, column=4, value=value / 100)
            cell.number_format = PCT4

            sheet.cell(
                row=row + 2, column=1, value='Desvío (p.p.):'
            ).font = BODY_FONT
            cell = sheet.cell(row=row + 2, column=2, value=f'=E{row_idx}*100')
            cell.number_format = '0.0000'
            sheet.cell(
                row=row + 2, column=3, value='Faixas 0,1%:'
            ).font = BODY_FONT
            cell = sheet.cell(row=row + 2, column=4, value=f'=F{row_idx}')
            cell.number_format = '0'

            sheet.cell(
                row=row + 3, column=1, value='Penalidad:'
            ).font = BODY_FONT
            cell = sheet.cell(row=row + 3, column=2, value=penalidade)
            cell.number_format = '0'
            sheet.cell(
                row=row + 3, column=3, value='Meta atingida?'
            ).font = BODY_FONT
            sheet.cell(
                row=row + 3, column=4, value='Sim' if atingido else 'Não'
            )

            row += 5
            row_idx += 1


def _write_note_nivel(
    sheet: Worksheet, row: int, entries: list[tuple[str, WholeIndicatorMode]]
) -> None:
    niveles = sorted({_NIVEL_BY_CATEGORIA.get(ck, '—') for ck, _e in entries})
    hoja = '; '.join(niveles)
    sheet.merge_cells(start_row=row, start_column=1, end_row=row, end_column=8)
    cell = sheet.cell(
        row=row,
        column=1,
        value=(
            'Categoría NOC/SOC → nivel único '
            f'{hoja}. Este indicador no admite N1 ni N2; por eso no hay '
            'subtotales por nivel en esta aba.'
        ),
    )
    cell.font = NOTE_FONT
    cell.fill = ORANGE_FILL
    cell.alignment = Alignment(wrap_text=True)


def _write_precomputed_audit_sheet(
    workbook: Workbook,
    sheet_name: str,
    categorias: CategoriasFile,
    entries: list[tuple[str, WholeIndicatorMode]],
    calculation: PrecomputedTableCalculation,
    target_operator: str,
    target_value: float,
    rows: list[dict[str, str]],
    contract: str,
    periodo: PeriodoAfericao | None,
    raw_csv_path: Path,
    generated_at: datetime,
) -> None:
    sheet = workbook.create_sheet(title=sheet_name)
    sheet.sheet_view.showGridLines = False
    for col, width in _COLUMN_WIDTHS.items():
        sheet.column_dimensions[cl(col)].width = width

    label = categorias.categorias[entries[0][0]].label
    write_section_1_identificacao(
        sheet,
        title=f'{safe_excel_text(label)} – Disponibilidad de sistema/servicio',
        rows=rows,
        contract=contract,
        periodo=periodo,
        raw_csv_path=raw_csv_path,
        generated_at=generated_at,
    )

    data_start = _write_table(
        sheet,
        start_row=11,
        categorias=categorias,
        entries=entries,
        calculation=calculation,
        target_operator=target_operator,
        target_value=target_value,
        rows=rows,
    )
    _write_memoria_penalidad(
        sheet,
        start_row=data_start + 2,
        categorias=categorias,
        entries=entries,
        calculation=calculation,
        target_operator=target_operator,
        target_value=target_value,
        rows=rows,
        data_start=data_start,
    )
    _write_note_nivel(sheet, sheet.max_row + 2, entries)
