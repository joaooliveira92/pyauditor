"""Renderer precomputed_table do sintetico — extraído de
`excel/sintetico/workbook.py` (ticket 04 SRP).
"""

from __future__ import annotations

from math import isnan
from typing import Final

from openpyxl import Workbook

from pyauditor.config.categorias import CategoriasFile, WholeIndicatorMode
from pyauditor.config.models import PrecomputedTableCalculation
from pyauditor.engine.strategies import parse_decimal
from pyauditor.excel._style import new_sheet, write_row
from pyauditor.excel.sintetico._sheets._shared import (
    _NIVEL_BY_CATEGORIA,
    meta_atingida_display,
)
from pyauditor.excel.sintetico._stats import fmt_pt_br

_PRECOMPUTED_COLUMNS: Final[tuple[str, ...]] = (
    'Categoria',
    'Nível',
    'Item',
    'Resultado',
    'Meta atingida?',
    'Penalidade',
)


def _write_precomputed_table_sheet(
    workbook: Workbook,
    sheet_name: str,
    categorias_file: CategoriasFile,
    entries: list[tuple[str, WholeIndicatorMode]],
    calculation: PrecomputedTableCalculation,
    target_operator: str,
    target_value: float,
    rows: list[dict[str, str]],
) -> None:
    """INMS 1.4/1.5/1.9/1.13: uma linha por `name_column` (o mesmo dado que a
    medição oficial lê — `PrecomputedTableStrategy`), em vez do colapso
    "(indicador inteiro)"/traços. "Meta atingida?" reusa `meets_target`
    contra `target`, não a coluna crua `atingiu_meta` do CSV."""
    sheet = new_sheet(workbook, sheet_name, _PRECOMPUTED_COLUMNS)
    row_idx = 2
    for categoria_key, _entry in entries:
        categoria = categorias_file.categorias[categoria_key]
        nivel = _NIVEL_BY_CATEGORIA.get(categoria_key)
        for row in rows:
            raw_value = row.get(calculation.result_column, '')
            if not raw_value.strip():
                # linhas vazias/placeholder (';' sobrando), sem medição
                continue
            value = parse_decimal(raw_value)
            if isnan(value):
                continue

            name = (
                row.get(calculation.name_column, '')
                if calculation.name_column
                else ''
            )
            resultado_display = (
                f'{fmt_pt_br(value)}%'
                if calculation.result_is_percent
                else fmt_pt_br(value, decimals=0)
            )
            meta_display = (
                meta_atingida_display(value, target_operator, target_value)
                if calculation.result_is_percent
                else '—'
            )
            penalidade_raw = (
                row.get(calculation.penalty_column, '')
                if calculation.penalty_column
                else ''
            )
            penalidade_value = (
                parse_decimal(penalidade_raw)
                if penalidade_raw.strip()
                else float('nan')
            )
            penalidade_display = (
                '—'
                if isnan(penalidade_value)
                else fmt_pt_br(penalidade_value, decimals=0)
            )

            write_row(
                sheet,
                row_idx,
                (
                    categoria.label,
                    nivel or '',
                    name,
                    resultado_display,
                    meta_display,
                    penalidade_display,
                ),
            )
            row_idx += 1
