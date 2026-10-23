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


def filter_rows(
    rows: list[dict[str, str]], column_filter: Filter | None
) -> list[dict[str, str]]:
    if column_filter is None:
        return rows
    # ⚡ Bolt: otimização de performance.
    # Constrói o predicado do filtro uma única vez fora do loop, evitando
    # checagens repetidas de `isinstance` e convertendo a lista de `ColumnIn`
    # em `set` para busca O(1) em datasets com milhares de linhas.
    matcher = _build_matcher(column_filter)
    return [row for row in rows if matcher(row)]


def _build_matcher(column_filter: Filter) -> Callable[[dict[str, str]], bool]:
    col = column_filter.column
    if isinstance(column_filter, ColumnEquals):
        equals = column_filter.equals
        return lambda row: row.get(col, '').strip() == equals
    if isinstance(column_filter, ColumnNotEquals):
        not_equals = column_filter.not_equals
        return lambda row: row.get(col, '').strip() != not_equals
    if isinstance(column_filter, ColumnContains):
        contains = column_filter.contains
        return lambda row: contains in row.get(col, '')
    if isinstance(column_filter, ColumnIn):
        in_set = set(column_filter.in_values)
        return lambda row: row.get(col, '').strip() in in_set
    if isinstance(column_filter, DurationAtMost):
        max_seconds = column_filter.max_seconds
        return lambda row: _matches_duration(row.get(col, ''), max_seconds)
    raise TypeError(f'Filtro não suportado: {type(column_filter).__name__}')


def _matches_duration(value: str, max_seconds: int) -> bool:
    seconds = _parse_duration_seconds(value)
    return seconds is not None and seconds <= max_seconds


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
