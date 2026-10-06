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


def _matches(row: dict[str, str], column_filter: Filter) -> bool:
    return _build_matcher(column_filter)(row)


def _build_matcher(column_filter: Filter) -> Callable[[dict[str, str]], bool]:
    # ⚡ Bolt: otimização de performance.
    # Avalia o tipo de filtro e extrai atributos/conjuntos uma única vez
    # antes do loop de linhas. Para ColumnIn, converte in_values de list
    # para set (busca O(1) em vez de busca linear O(N) por linha) e evita
    # isinstance repetido.
    col = column_filter.column
    if isinstance(column_filter, ColumnEquals):
        target_eq = column_filter.equals
        return lambda row: row.get(col, '').strip() == target_eq
    if isinstance(column_filter, ColumnNotEquals):
        target_neq = column_filter.not_equals
        return lambda row: row.get(col, '').strip() != target_neq
    if isinstance(column_filter, ColumnContains):
        target_sub = column_filter.contains
        return lambda row: target_sub in row.get(col, '')
    if isinstance(column_filter, ColumnIn):
        target_set = set(column_filter.in_values)
        return lambda row: row.get(col, '').strip() in target_set
    if isinstance(column_filter, DurationAtMost):
        max_sec = column_filter.max_seconds
        return lambda row: (
            (sec := _parse_duration_seconds(row.get(col, ''))) is not None
            and sec <= max_sec
        )
    raise ValueError(f'Tipo de filtro desconhecido: {type(column_filter)}')


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
