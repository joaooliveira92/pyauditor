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
    """Filtra linhas com base em um `column_filter`.

    Otimizado para avaliar a variante do filtro uma única vez fora do loop,
    evitando checagens `isinstance` repetidas por linha e convertendo
    `in_values` para `set` (busca O(1) em vez de O(N)).
    """
    if column_filter is None or not rows:
        return rows

    col = column_filter.column

    if isinstance(column_filter, ColumnEquals):
        eq = column_filter.equals
        return [row for row in rows if row.get(col, '').strip() == eq]

    if isinstance(column_filter, ColumnNotEquals):
        neq = column_filter.not_equals
        return [row for row in rows if row.get(col, '').strip() != neq]

    if isinstance(column_filter, ColumnContains):
        contains = column_filter.contains
        return [row for row in rows if contains in row.get(col, '')]

    if isinstance(column_filter, ColumnIn):
        in_set = set(column_filter.in_values)
        return [row for row in rows if row.get(col, '').strip() in in_set]

    max_secs = column_filter.max_seconds
    return [
        row
        for row in rows
        if (s := _parse_duration_seconds(row.get(col, ''))) is not None
        and s <= max_secs
    ]


def _matches(row: dict[str, str], column_filter: Filter) -> bool:
    return bool(filter_rows([row], column_filter))


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
