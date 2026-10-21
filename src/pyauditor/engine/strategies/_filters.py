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
    """Filtra linhas de um dataset aplicando um `Filter` configurado.

    Aplica um filtro no dataset preservando a ordem das linhas.
    """
    if column_filter is None or not rows:
        return rows

    column = column_filter.column

    # ⚡ Bolt: otimização de performance.
    # Despacha a filtragem inspecionando o tipo do filtro uma única vez fora do
    # loop de linhas, evitando a invocação repetida de `_matches` e checagens
    # de `isinstance` a cada elemento do dataset. Para `ColumnIn`, pré-converte
    # `in_values` para `set` fora do loop, transformando a busca linear O(M) em
    # busca constante O(1).
    if isinstance(column_filter, ColumnEquals):
        target_eq = column_filter.equals
        return [r for r in rows if (r.get(column) or '').strip() == target_eq]

    if isinstance(column_filter, ColumnIn):
        target_set = set(column_filter.in_values)
        return [r for r in rows if (r.get(column) or '').strip() in target_set]

    if isinstance(column_filter, ColumnContains):
        target_contains = column_filter.contains
        return [r for r in rows if target_contains in (r.get(column) or '')]

    if isinstance(column_filter, ColumnNotEquals):
        target_neq = column_filter.not_equals
        return [r for r in rows if (r.get(column) or '').strip() != target_neq]

    if isinstance(column_filter, DurationAtMost):
        max_seconds = column_filter.max_seconds
        retained: list[dict[str, str]] = []
        for r in rows:
            secs = _parse_duration_seconds(r.get(column) or '')
            if secs is not None and secs <= max_seconds:
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
