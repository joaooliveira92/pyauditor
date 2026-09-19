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
    if column_filter is None:
        return rows

    # ⚡ Bolt: otimização de performance.
    # Despacha o filtro pelo tipo exato evitando o dispatch dinâmico /
    # isinstance genérico de _matches a cada iteração do loop sobre
    # dezenas de milhares de linhas.
    # Além disso, para ColumnIn converte a lista em set uma única vez
    # antes do loop (reduzindo complexidade de pertencimento de O(N) para O(1)).
    col = column_filter.column

    if isinstance(column_filter, ColumnEquals):
        target = column_filter.equals
        return [r for r in rows if (r.get(col) or '').strip() == target]

    if isinstance(column_filter, ColumnNotEquals):
        not_target = column_filter.not_equals
        return [r for r in rows if (r.get(col) or '').strip() != not_target]

    if isinstance(column_filter, ColumnContains):
        sub = column_filter.contains
        return [r for r in rows if sub in r.get(col, '')]

    if isinstance(column_filter, ColumnIn):
        in_set = set(column_filter.in_values)
        return [r for r in rows if r.get(col, '').strip() in in_set]

    if isinstance(column_filter, DurationAtMost):
        max_sec = column_filter.max_seconds
        retained: list[dict[str, str]] = []
        for r in rows:
            sec = _parse_duration_seconds(r.get(col, ''))
            if sec is not None and sec <= max_sec:
                retained.append(r)
        return retained

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
