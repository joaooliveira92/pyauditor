"""Applies a `Filter` (`ColumnEquals` | `ColumnNotEquals` | `ColumnContains` |
`ColumnIn` | `DurationAtMost`) from a calculation config to CSV rows.
"""

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

    # ⚡ Bolt: otimização de performance.
    # Evita chamadas repetidas a isinstance() e lookups de atributos a cada
    # linha do dataset despachando o tipo de filtro uma única vez fora do loop.
    # Para `ColumnIn`, converte a lista de valores em `set` para que a busca
    # seja O(1) em vez de busca linear O(K) por linha.
    if isinstance(column_filter, ColumnEquals):
        col, target = column_filter.column, column_filter.equals
        return [row for row in rows if row.get(col, '').strip() == target]

    if isinstance(column_filter, ColumnNotEquals):
        col, target = column_filter.column, column_filter.not_equals
        return [row for row in rows if row.get(col, '').strip() != target]

    if isinstance(column_filter, ColumnContains):
        col, target = column_filter.column, column_filter.contains
        return [row for row in rows if target in row.get(col, '')]

    if isinstance(column_filter, ColumnIn):
        col = column_filter.column
        in_set = set(column_filter.in_values)
        return [row for row in rows if row.get(col, '').strip() in in_set]

    if isinstance(column_filter, DurationAtMost):
        col, max_sec = column_filter.column, column_filter.max_seconds
        return [
            row
            for row in rows
            if (sec := _parse_duration_seconds(row.get(col, ''))) is not None
            and sec <= max_sec
        ]

    return [row for row in rows if _matches(row, column_filter)]


def _matches(row: dict[str, str], column_filter: Filter) -> bool:
    value = row.get(column_filter.column, '')
    if isinstance(column_filter, ColumnEquals):
        return value.strip() == column_filter.equals
    if isinstance(column_filter, ColumnNotEquals):
        return value.strip() != column_filter.not_equals
    if isinstance(column_filter, ColumnContains):
        return column_filter.contains in value
    if isinstance(column_filter, ColumnIn):
        return value.strip() in column_filter.in_values
    seconds = _parse_duration_seconds(value)
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
