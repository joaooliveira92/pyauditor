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

    # ⚡ Bolt: otimização de performance.
    # Compila o predicado do filtro uma única vez antes do loop de linhas.
    # Evita checagens dinâmicas repetidas de isinstance() e converte in_values
    # para conjunto O(1) em filtros ColumnIn.
    predicate = _compile_filter(column_filter)
    return [row for row in rows if predicate(row)]


def _matches(row: dict[str, str], column_filter: Filter) -> bool:
    """Avalia se uma única linha atende ao filtro."""
    return _compile_filter(column_filter)(row)


def _compile_filter(column_filter: Filter) -> Callable[[dict[str, str]], bool]:
    """Compila uma função predicado otimizada para o filtro fornecido."""
    col = getattr(column_filter, 'column', None)

    if isinstance(column_filter, ColumnEquals):
        target = column_filter.equals
        return lambda row: (row.get(col) or '').strip() == target

    if isinstance(column_filter, ColumnNotEquals):
        target = column_filter.not_equals
        return lambda row: (row.get(col) or '').strip() != target

    if isinstance(column_filter, ColumnContains):
        substr = column_filter.contains
        return lambda row: substr in (row.get(col) or '')

    if isinstance(column_filter, ColumnIn):
        val_set = set(column_filter.in_values)
        return lambda row: (row.get(col) or '').strip() in val_set

    if isinstance(column_filter, DurationAtMost):
        max_sec = column_filter.max_seconds

        def _check_duration(row: dict[str, str]) -> bool:
            sec = _parse_duration_seconds(row.get(col) or '')
            return sec is not None and sec <= max_sec

        return _check_duration

    # Fallback genérico para suportar extensões personalizadas de filtro
    def _fallback_matcher(row: dict[str, str]) -> bool:
        col_name = getattr(column_filter, 'column', '')
        value = row.get(col_name, '') or ''
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

    return _fallback_matcher


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
