"""Renderer INMS 1.14 (multi-ativo x categoria) — extraído de
`excel/sintetico/workbook.py` (ticket 04 SRP).
"""

from __future__ import annotations

from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from pyauditor.config.categorias import (
    CategoriasFile,
    WholeIndicatorMode,
)
from pyauditor.excel._style import LABEL_FONT, new_sheet, write_row
from pyauditor.excel.sintetico._sheets._shared import (
    _ATIVO_COLUMNS,
    _ATIVO_SUBTOTAL_COLUMNS,
    _INMS_1_14_CATEGORIA_ORDER,
    _NIVEL_BY_CATEGORIA,
)
from pyauditor.excel.sintetico._stats import (
    NivelAccumulator,
    compute_stats,
    format_duracao,
    format_pct_bruto,
    format_row,
)


def _write_ativo_subtotals(
    sheet: Worksheet,
    start_row: int,
    order: list[str],
    labels: dict[str, str],
    accumulators: dict[str, NivelAccumulator],
) -> None:
    header_cell = sheet.cell(row=start_row, column=1, value="Subtotais por Categoria")
    header_cell.font = LABEL_FONT
    for col_idx, column in enumerate(_ATIVO_SUBTOTAL_COLUMNS, start=1):
        cell = sheet.cell(row=start_row + 1, column=col_idx, value=column)
        cell.font = LABEL_FONT

    row_idx = start_row + 2
    for categoria_key in order:
        acc = accumulators.get(categoria_key)
        if acc is None:
            continue
        dentro = acc.dentro if acc.tem_prazo else None
        fora = acc.fora if acc.tem_prazo else None
        pct_display = format_pct_bruto(dentro, fora)
        tempo_display = (
            format_duracao(acc.duracao_total_segundos / acc.duracao_contagem)
            if acc.duracao_contagem > 0
            else "—"
        )
        write_row(
            sheet,
            row_idx,
            (
                labels[categoria_key],
                acc.linhas,
                dentro if dentro is not None else "—",
                fora if fora is not None else "—",
                pct_display,
                tempo_display,
            ),
            expected_columns=len(_ATIVO_SUBTOTAL_COLUMNS),
        )
        row_idx += 1

def _write_multi_ativo_sheet(
    workbook: Workbook,
    sheet_name: str,
    categorias_file: CategoriasFile,
    entries: list[tuple[str, WholeIndicatorMode]],
    ativo_column: str,
    fieldnames: list[str],
    rows: list[dict[str, str]],
    accepted_ids: set[int],
) -> None:
    """INMS 1.14 (spec §14.5): produto cartesiano ativo x categoria — as 6
    medições por ativo (já presentes no CSV, uma linha por ativo) são
    duplicadas/rotuladas sob cada categoria à qual o INMS pertence, sem
    recalcular nada. Bloco NOC/SOC antes do bloco Operação N3."""
    sheet = new_sheet(workbook, sheet_name, _ATIVO_COLUMNS)
    row_idx = 2
    accumulators: dict[str, NivelAccumulator] = {}
    labels: dict[str, str] = {}

    # Ordem de primeira aparição no CSV (Anexo D já lista os 6 ativos numa
    # ordem fixa — File Server, Telefonia, Mensageria, etc. — preservada
    # aqui em vez de reordenar alfabeticamente).
    ativos = list(dict.fromkeys(row[ativo_column] for row in rows if row.get(ativo_column)))

    ordered_entries = sorted(
        entries,
        key=lambda item: (
            _INMS_1_14_CATEGORIA_ORDER.index(item[0])
            if item[0] in _INMS_1_14_CATEGORIA_ORDER
            else len(_INMS_1_14_CATEGORIA_ORDER),
            item[0],
        ),
    )

    for categoria_key, _entry in ordered_entries:
        categoria = categorias_file.categorias[categoria_key]
        nivel = _NIVEL_BY_CATEGORIA.get(categoria_key)
        labels[categoria_key] = categoria.label
        for ativo in ativos:
            ativo_rows = [row for row in rows if row.get(ativo_column) == ativo]
            stats = compute_stats(ativo_rows, fieldnames, accepted_ids)
            linhas, dentro, fora, pct, tempo = format_row(stats)
            write_row(
                sheet,
                row_idx,
                (
                    categoria.label,
                    nivel or "",
                    ativo,
                    linhas,
                    dentro,
                    fora,
                    pct,
                    tempo,
                ),
            )
            row_idx += 1
            current = accumulators.get(categoria_key, NivelAccumulator())
            accumulators[categoria_key] = current.add(stats)

    if accumulators:
        order = [categoria_key for categoria_key, _entry in ordered_entries]
        _write_ativo_subtotals(sheet, row_idx + 1, order, labels, accumulators)

