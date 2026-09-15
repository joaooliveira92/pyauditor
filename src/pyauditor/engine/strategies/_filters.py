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
    # Iça a verificação de tipo de filtro e a extração de propriedades para
    # fora do loop de iteração das linhas do dataset, evitando inspecionar o
    # tipo de `column_filter` e acessar seus atributos repetidamente.
    col = column_filter.column

    if isinstance(column_filter, ColumnEquals):
        expected = column_filter.equals
        return [row for row in rows if row.get(col, '').strip() == expected]

    if isinstance(column_filter, ColumnNotEquals):
        not_expected = column_filter.not_equals
        return [row for row in rows if row.get(col, '').strip() != not_expected]

    if isinstance(column_filter, ColumnContains):
        contains = column_filter.contains
        return [row for row in rows if contains in row.get(col, '')]

    if isinstance(column_filter, ColumnIn):
        # Converte a lista em conjunto uma única vez antes do loop para
        # busca em tempo constante O(1).
        in_values_set = set(column_filter.in_values)
        return [
            row for row in rows if row.get(col, '').strip() in in_values_set
        ]

    if isinstance(column_filter, DurationAtMost):
        max_seconds = column_filter.max_seconds
        return [
            row
            for row in rows
            if (secs := _parse_duration_seconds(row.get(col, ''))) is not None
            and secs <= max_seconds
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
    # ⚡ Bolt: otimização de performance.
    # Evita geradores intermediários e validações redundantes de dígitos
    # convertendo diretamente os elementos via indexação de lista com bloco
    # try/except ValueError.
    parts = value.strip().split(':')
    if len(parts) != 3:
        return None
    try:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except ValueError:
        return None
