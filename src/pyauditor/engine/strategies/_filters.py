"""Applies a `Filter` (`ColumnEquals` | `ColumnNotEquals` | `ColumnContains` |
`ColumnIn` | `DurationAtMost`) from a calculation config to CSV rows.
"""

from pyauditor.config.models import (
    ColumnContains,
    ColumnEquals,
    ColumnIn,
    ColumnNotEquals,
    Filter,
)


def filter_rows(
    rows: list[dict[str, str]], column_filter: Filter | None
) -> list[dict[str, str]]:
    if column_filter is None:
        return rows

    col = column_filter.column
    # ⚡ Bolt: otimização de performance.
    # Avalia o tipo de filtro uma única vez fora do loop de linhas em vez de
    # reavaliar `isinstance` para cada linha do dataset, e converte a lista
    # `in_values` em `set` para buscas O(1) em vez de buscas lineares O(K).
    if isinstance(column_filter, ColumnEquals):
        target = column_filter.equals
        return [row for row in rows if row.get(col, '').strip() == target]
    if isinstance(column_filter, ColumnNotEquals):
        target = column_filter.not_equals
        return [row for row in rows if row.get(col, '').strip() != target]
    if isinstance(column_filter, ColumnContains):
        substr = column_filter.contains
        return [row for row in rows if substr in row.get(col, '')]
    if isinstance(column_filter, ColumnIn):
        values_set = set(column_filter.in_values)
        return [row for row in rows if row.get(col, '').strip() in values_set]

    # DurationAtMost
    max_sec = column_filter.max_seconds
    return [
        row
        for row in rows
        if (sec := _parse_duration_seconds(row.get(col, ''))) is not None
        and sec <= max_sec
    ]


def _matches(row: dict[str, str], column_filter: Filter) -> bool:
    """Valida se uma única linha satisfaz *column_filter*."""
    col = column_filter.column
    if isinstance(column_filter, ColumnEquals):
        return row.get(col, '').strip() == column_filter.equals
    if isinstance(column_filter, ColumnNotEquals):
        return row.get(col, '').strip() != column_filter.not_equals
    if isinstance(column_filter, ColumnContains):
        return column_filter.contains in row.get(col, '')
    if isinstance(column_filter, ColumnIn):
        return row.get(col, '').strip() in set(column_filter.in_values)
    seconds = _parse_duration_seconds(row.get(col, ''))
    return seconds is not None and seconds <= column_filter.max_seconds


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
