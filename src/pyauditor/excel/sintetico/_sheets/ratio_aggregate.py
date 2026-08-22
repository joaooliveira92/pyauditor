"""Renderer ratio/sum (INMS 1.6) com subtract — extraído de
`excel/sintetico/workbook.py` (ticket 04 SRP).
"""

from __future__ import annotations

from openpyxl import Workbook

from pyauditor.config.categorias import CategoriasFile, WholeIndicatorMode
from pyauditor.config.models import RatioCalculation
from pyauditor.engine.strategies import filter_rows, parse_decimal, safe_pct
from pyauditor.excel._style import new_sheet, write_row
from pyauditor.excel.sintetico._sheets._shared import (
    _NIVEL_BY_CATEGORIA,
    meta_atingida_display,
)
from pyauditor.excel.sintetico._stats import fmt_pt_br


def _write_ratio_aggregate_sheet(
    workbook: Workbook,
    sheet_name: str,
    categorias_file: CategoriasFile,
    entries: list[tuple[str, WholeIndicatorMode]],
    calculation: RatioCalculation,
    target_operator: str,
    target_value: float,
    rows: list[dict[str, str]],
) -> None:
    """INMS 1.6 (e qualquer futuro `ratio`/`sum` com
    `sum_numerator_subtract_column`): uma linha por valor distinto da coluna
    de `denominator_filter` (ex. "Acordo de Nível de Serviço"), agregando os
    CSVs elegíveis por grupo com a mesma aritmética de
    `RatioStrategy._aggregate`, em vez do colapso "(indicador inteiro)"."""
    assert calculation.denominator_filter is not None
    assert calculation.sum_numerator_column is not None
    assert calculation.sum_numerator_subtract_column is not None
    group_column = calculation.denominator_filter.column
    numerator_column = calculation.sum_numerator_column
    subtract_column = calculation.sum_numerator_subtract_column

    columns = (
        "Categoria",
        "Nível",
        group_column,
        numerator_column,
        subtract_column,
        "% resultado",
        "Meta atingida?",
    )
    sheet = new_sheet(workbook, sheet_name, columns)
    row_idx = 2

    eligible_rows = filter_rows(rows, calculation.denominator_filter)
    grupos = list(
        dict.fromkeys(row[group_column] for row in eligible_rows if row.get(group_column))
    )

    for categoria_key, _entry in entries:
        categoria = categorias_file.categorias[categoria_key]
        nivel = _NIVEL_BY_CATEGORIA.get(categoria_key)
        for grupo in grupos:
            grupo_rows = [row for row in eligible_rows if row[group_column] == grupo]
            total = sum(parse_decimal(row.get(numerator_column, "") or "0") for row in grupo_rows)
            subtraido = sum(
                parse_decimal(row.get(subtract_column, "") or "0") for row in grupo_rows
            )
            pct = safe_pct(total - subtraido, total)
            meta_display = meta_atingida_display(pct, target_operator, target_value)
            write_row(
                sheet,
                row_idx,
                (
                    categoria.label,
                    nivel or "",
                    grupo,
                    int(total),
                    int(subtraido),
                    f"{fmt_pt_br(pct)}%",
                    meta_display,
                ),
            )
            row_idx += 1
