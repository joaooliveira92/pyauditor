"""Applies a `Filter` (`ColumnEquals` | `ColumnNotEquals` | `ColumnContains` |
`ColumnIn` | `DurationAtMost`) from a calculation config to CSV rows.
"""

from collections.abc import Callable

from pyauditor.config.models import (
    ColumnContains,
    ColumnEquals,
    ColumnIn,
    ColumnNotEquals,
    DurationAtMost,
    Filter,
)


def compile_filter(column_filter: Filter) -> Callable[[dict[str, str]], bool]:
    """⚡ Bolt: Compila um modelo Filter em uma closure predicada otimizada.

    Pré-extrai atributos do filtro, converte `in_values` para `set` garantindo
    busca O(1), e elimina checagens de `isinstance` dentro de loops de linhas.
    """
    col = column_filter.column
    if isinstance(column_filter, ColumnEquals):
        target = column_filter.equals
        return lambda row: row.get(col, '').strip() == target
    if isinstance(column_filter, ColumnNotEquals):
        target = column_filter.not_equals
        return lambda row: row.get(col, '').strip() != target
    if isinstance(column_filter, ColumnContains):
        target = column_filter.contains
        return lambda row: target in row.get(col, '')
    if isinstance(column_filter, ColumnIn):
        in_set = set(column_filter.in_values)
        return lambda row: row.get(col, '').strip() in in_set
    if isinstance(column_filter, DurationAtMost):
        max_sec = column_filter.max_seconds
        return lambda row: (
            (sec := _parse_duration_seconds(row.get(col, ''))) is not None
            and sec <= max_sec
        )
    raise TypeError(
        f'Tipo de filtro não suportado: {type(column_filter).__name__}'
    )


def filter_rows(
    rows: list[dict[str, str]], column_filter: Filter | None
) -> list[dict[str, str]]:
    if column_filter is None:
        return rows
    predicate = compile_filter(column_filter)
    return [row for row in rows if predicate(row)]


def _matches(row: dict[str, str], column_filter: Filter) -> bool:
    """Delega para `compile_filter` na avaliação de uma única linha."""
    return compile_filter(column_filter)(row)


def _parse_duration_seconds(value: str) -> int | None:
    """Parses `H:MM:SS` durations (as used by the telephony CSVs' `ESPERA`
    column) into seconds. Not a general duration parser — a leading days
    field (`D:HH:MM:SS`, as seen in the availability CSVs) would be parsed
    incorrectly, but no `DurationAtMost` filter is used against those.
    """
    parts = value.strip().split(':')
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        return None
    hours, minutes, secs = (int(p) for p in parts)
    return hours * 3600 + minutes * 60 + secs
