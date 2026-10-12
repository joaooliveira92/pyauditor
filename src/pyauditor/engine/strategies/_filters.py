"""Applies a `Filter` (`ColumnEquals` | `ColumnNotEquals` | `ColumnContains` |
`ColumnIn` | `DurationAtMost`) from a calculation config to CSV rows.
"""

from __future__ import annotations

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

    # ⚡ Bolt: otimização de performance.
    # Despacha o filtro uma única vez por chamada a `filter_rows`, evitando
    # checagens repetidas de `isinstance` e acessos de atributos por linha.
    col = column_filter.column

    if isinstance(column_filter, ColumnEquals):
        equals_val = column_filter.equals
        return [row for row in rows if row.get(col, '').strip() == equals_val]

    if isinstance(column_filter, ColumnNotEquals):
        not_equals_val = column_filter.not_equals
        return [
            row for row in rows if row.get(col, '').strip() != not_equals_val
        ]

    if isinstance(column_filter, ColumnContains):
        contains_val = column_filter.contains
        return [row for row in rows if contains_val in row.get(col, '')]

    if isinstance(column_filter, ColumnIn):
        in_values = (
            column_filter.in_values
            if isinstance(column_filter.in_values, (set, frozenset))
            else set(column_filter.in_values)
        )
        return [row for row in rows if row.get(col, '').strip() in in_values]

    max_secs = column_filter.max_seconds
    return [
        row
        for row in rows
        if (sec := _parse_duration_seconds(row.get(col, ''))) is not None
        and sec <= max_secs
    ]


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
    # ⚡ Bolt: otimização de performance.
    # Substitui geradores e `all(...)` por indexação direta de lista de 3
    # elementos para evitar alocações de iteradores por linha.
    if len(parts) != 3 or not (
        parts[0].isdigit() and parts[1].isdigit() and parts[2].isdigit()
    ):
        return None
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
