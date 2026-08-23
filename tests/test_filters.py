"""Testes unitários de `filter_rows`, incl. o filtro de duração."""

from pyauditor.config.models import (
    ColumnContains,
    ColumnEquals,
    ColumnIn,
    ColumnNotEquals,
    DurationAtMost,
)
from pyauditor.engine.strategies._filters import filter_rows

ROWS: list[dict[str, str]] = [
    {'SLA': 'Alta', 'No prazo': 'S', 'ESPERA': '00:01:30'},
    {'SLA': 'Baixa', 'No prazo': 'N', 'ESPERA': '01:00:00'},
    {'SLA': 'Alta', 'No prazo': 'N', 'ESPERA': '00:30:00'},
]


def test_filter_rows_none_returns_rows_unchanged() -> None:
    assert filter_rows(ROWS, None) == ROWS


def test_filter_rows_column_equals() -> None:
    result = filter_rows(ROWS, ColumnEquals(column='No prazo', equals='S'))
    assert result == [ROWS[0]]


def test_filter_rows_column_not_equals() -> None:
    result = filter_rows(
        ROWS, ColumnNotEquals(column='No prazo', not_equals='S')
    )
    assert result == [ROWS[1], ROWS[2]]


def test_filter_rows_column_contains() -> None:
    result = filter_rows(ROWS, ColumnContains(column='SLA', contains='Alta'))
    assert result == [ROWS[0], ROWS[2]]


def test_filter_rows_column_in() -> None:
    result = filter_rows(
        ROWS, ColumnIn(column='No prazo', in_values=['S', 'N'])
    )
    assert result == ROWS


def test_filter_rows_column_in_excludes_non_members() -> None:
    result = filter_rows(ROWS, ColumnIn(column='SLA', in_values=['Baixa']))
    assert result == [ROWS[1]]


def test_filter_rows_duration_at_most_filters_by_seconds() -> None:
    result = filter_rows(ROWS, DurationAtMost(column='ESPERA', max_seconds=600))
    # 00:01:30 = 90s (<= 600) e 00:30:00 = 1800s > 600s; 01:00:00 = 3600s.
    assert result == [ROWS[0]]


def test_filter_rows_duration_unparseable_is_excluded() -> None:
    rows = [{'ESPERA': 'not-a-duration'}, *ROWS]
    result = filter_rows(rows, DurationAtMost(column='ESPERA', max_seconds=90))
    assert result == [ROWS[0]]
