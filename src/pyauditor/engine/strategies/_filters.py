"""Applies a `Filter` (`ColumnEquals` | `ColumnNotEquals` | `ColumnContains` |
`ColumnIn` | `DurationAtMost`) from a calculation config to CSV rows.
"""

from collections.abc import Callable

from pyauditor.config.models import (
    ColumnContains,
    ColumnEquals,
    ColumnIn,
    ColumnNotEquals,
    Filter,
)


def _compile_matcher(
    column_filter: Filter,
) -> Callable[[dict[str, str]], bool]:
    # ⚡ Bolt: otimização de performance.
    # Pre-compila o predicado do filtro para extrair o nome da coluna
    # uma única vez, evitar checagens repetidas de `isinstance` a cada
    # linha do dataset e converter `in_values` de `list` para `set`
    # (busca em tabela hash O(1) em vez de busca linear O(N)).
    col = column_filter.column
    if isinstance(column_filter, ColumnEquals):
        target = column_filter.equals
        return lambda row: (row.get(col) or '').strip() == target
    if isinstance(column_filter, ColumnNotEquals):
        target = column_filter.not_equals
        return lambda row: (row.get(col) or '').strip() != target
    if isinstance(column_filter, ColumnContains):
        target = column_filter.contains
        return lambda row: target in (row.get(col) or '')
    if isinstance(column_filter, ColumnIn):
        in_set = set(column_filter.in_values)
        return lambda row: (row.get(col) or '').strip() in in_set
    max_seconds = column_filter.max_seconds
    return lambda row: (
        (secs := _parse_duration_seconds(row.get(col, ''))) is not None
        and secs <= max_seconds
    )


def filter_rows(
    rows: list[dict[str, str]], column_filter: Filter | None
) -> list[dict[str, str]]:
    if column_filter is None:
        return rows
    matcher = _compile_matcher(column_filter)
    return [row for row in rows if matcher(row)]


def _matches(row: dict[str, str], column_filter: Filter) -> bool:
    """Função utilitária interna para verificação de linha única."""
    return _compile_matcher(column_filter)(row)


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
