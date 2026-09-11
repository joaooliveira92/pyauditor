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
    matcher = _build_matcher(column_filter)
    return [row for row in rows if matcher(row)]


def _build_matcher(
    column_filter: Filter,
) -> Callable[[dict[str, str]], bool]:
    """⚡ Bolt: otimização de performance.

    Constrói um predicado pré-compilado fora do loop de linhas.
    Elimina verificações com `isinstance` e lookups de atributos a cada linha,
    além de converter `in_values` para `set` permitindo busca O(1).
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

        def _duration_matcher(row: dict[str, str]) -> bool:
            value = row.get(col, '')
            seconds = _parse_duration_seconds(value)
            return seconds is not None and seconds <= max_sec

        return _duration_matcher

    raise TypeError(f'Tipo de filtro não suportado: {type(column_filter)}')


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
