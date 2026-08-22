"""Renderers grupo-executor / whole-indicator / subtotais do sintetico —
extraídos de `excel/sintetico/workbook.py` (ticket 04 SRP).
"""

from __future__ import annotations

from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from pyauditor.categoria_filter import (
    GRUPO_EXECUTOR_COLUMN,
    compute_categoria_values,
)
from pyauditor.config.categorias import (
    CategoriasFile,
    GrupoExecutorMode,
    WholeIndicatorMode,
)
from pyauditor.excel._style import LABEL_FONT, new_sheet, write_row
from pyauditor.excel.sintetico._sheets._shared import (
    _COLUMNS,
    _NIVEL_BY_CATEGORIA,
    _NIVEL_ORDER,
    _OUTROS_LABEL,
    _SUBTOTAL_COLUMNS,
    _WHOLE_INDICATOR_LABEL,
)
from pyauditor.excel.sintetico._stats import (
    NivelAccumulator,
    compute_stats,
    format_duracao,
    format_pct_bruto,
    format_row,
)


def _write_grupo_executor_sheet(
    workbook: Workbook,
    sheet_name: str,
    categorias_file: CategoriasFile,
    grupo_executor_entries: list[tuple[str, GrupoExecutorMode]],
    whole_indicator_entries: list[tuple[str, WholeIndicatorMode]],
    fieldnames: list[str],
    rows: list[dict[str, str]],
    accepted_ids: set[int],
) -> None:
    sheet = new_sheet(workbook, sheet_name, _COLUMNS)
    row_idx = 2
    accumulators: dict[str, NivelAccumulator] = {}

    real_values = {row[GRUPO_EXECUTOR_COLUMN] for row in rows}
    per_categoria_values, outros_values = compute_categoria_values(
        grupo_executor_entries, real_values
    )

    def _emit(
        categoria_label: str,
        nivel: str | None,
        grupo: str,
        group_rows: list[dict[str, str]],
    ) -> None:
        nonlocal row_idx
        stats = compute_stats(group_rows, fieldnames, accepted_ids)
        linhas, dentro, fora, pct, tempo = format_row(stats)
        write_row(
            sheet,
            row_idx,
            (
                categoria_label,
                nivel or '',
                grupo,
                linhas,
                dentro,
                fora,
                pct,
                tempo,
            ),
        )
        row_idx += 1
        if nivel is not None:
            current = accumulators.get(nivel, NivelAccumulator())
            accumulators[nivel] = current.add(stats)

    for categoria_key, effective_values in per_categoria_values.items():
        categoria = categorias_file.categorias[categoria_key]
        nivel = _NIVEL_BY_CATEGORIA.get(categoria_key)
        for grupo in sorted(effective_values):
            group_rows = [
                row for row in rows if row[GRUPO_EXECUTOR_COLUMN] == grupo
            ]
            _emit(categoria.label, nivel, grupo, group_rows)

    for categoria_key, _entry in whole_indicator_entries:
        categoria = categorias_file.categorias[categoria_key]
        nivel = _NIVEL_BY_CATEGORIA.get(categoria_key)
        _emit(categoria.label, nivel, _WHOLE_INDICATOR_LABEL, rows)

    for grupo in sorted(outros_values):
        group_rows = [
            row for row in rows if row[GRUPO_EXECUTOR_COLUMN] == grupo
        ]
        _emit(_OUTROS_LABEL, None, grupo, group_rows)

    if accumulators:
        _write_subtotals(sheet, row_idx + 1, accumulators)


def _write_subtotals(
    sheet: Worksheet, start_row: int, accumulators: dict[str, NivelAccumulator]
) -> None:
    header_cell = sheet.cell(
        row=start_row, column=1, value='Subtotais por Nível'
    )
    header_cell.font = LABEL_FONT
    for col_idx, column in enumerate(_SUBTOTAL_COLUMNS, start=1):
        cell = sheet.cell(row=start_row + 1, column=col_idx, value=column)
        cell.font = LABEL_FONT

    row_idx = start_row + 2
    for nivel in _NIVEL_ORDER:
        acc = accumulators.get(nivel)
        if acc is None:
            continue
        dentro = acc.dentro if acc.tem_prazo else None
        fora = acc.fora if acc.tem_prazo else None
        pct_display = format_pct_bruto(dentro, fora)
        tempo_display = (
            format_duracao(acc.duracao_total_segundos / acc.duracao_contagem)
            if acc.duracao_contagem > 0
            else '—'
        )
        write_row(
            sheet,
            row_idx,
            (
                nivel,
                acc.linhas,
                dentro if dentro is not None else '—',
                fora if fora is not None else '—',
                pct_display,
                tempo_display,
            ),
            expected_columns=len(_SUBTOTAL_COLUMNS),
        )
        row_idx += 1


def _write_whole_indicator_sheet(
    workbook: Workbook,
    sheet_name: str,
    categorias_file: CategoriasFile,
    entries: list[tuple[str, WholeIndicatorMode]],
    fieldnames: list[str],
    rows: list[dict[str, str]],
    accepted_ids: set[int],
) -> None:
    sheet = new_sheet(workbook, sheet_name, _COLUMNS)
    stats = compute_stats(rows, fieldnames, accepted_ids)
    linhas, dentro, fora, pct, tempo = format_row(stats)
    row_idx = 2
    for categoria_key, _entry in entries:
        categoria = categorias_file.categorias[categoria_key]
        nivel = _NIVEL_BY_CATEGORIA.get(categoria_key)
        write_row(
            sheet,
            row_idx,
            (
                categoria.label,
                nivel or '',
                _WHOLE_INDICATOR_LABEL,
                linhas,
                dentro,
                fora,
                pct,
                tempo,
            ),
        )
        row_idx += 1
