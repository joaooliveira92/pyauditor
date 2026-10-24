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
    if column_filter is None or not rows:
        return rows
    predicate = _build_predicate(column_filter)
    return [row for row in rows if predicate(row)]


def _matches(row: dict[str, str], column_filter: Filter) -> bool:
    return _build_predicate(column_filter)(row)


def _build_predicate(column_filter: Filter) -> Callable[[dict[str, str]], bool]:
    col = column_filter.column
    # ⚡ Bolt: otimização de performance.
    # Constrói o predicado de filtragem uma única vez por filtro em vez de
    # avaliar isinstance/dispatch e buscas em lista para cada linha do dataset.
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
        # Transforma in_values (list) em set para buscas O(1) em vez de O(N).
        target_set = set(column_filter.in_values)
        return lambda row: row.get(col, '').strip() in target_set
    if isinstance(column_filter, DurationAtMost):
        max_secs = column_filter.max_seconds

        def _duration_predicate(row: dict[str, str]) -> bool:
            secs = _parse_duration_seconds(row.get(col, ''))
            return secs is not None and secs <= max_secs

        return _duration_predicate

    raise TypeError(f'Filtro não suportado: {type(column_filter).__name__}')


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
