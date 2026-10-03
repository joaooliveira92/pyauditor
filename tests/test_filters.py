from pyauditor.config.models import (
    ColumnContains,
    ColumnEquals,
    ColumnIn,
    ColumnNotEquals,
    DurationAtMost,
)
from pyauditor.engine.strategies._filters import _matches, filter_rows


def test_filter_rows_none_or_empty() -> None:
    rows = [{'a': '1'}]
    assert filter_rows(rows, None) == rows
    assert filter_rows([], ColumnEquals(column='a', equals='1')) == []


def test_filter_rows_column_equals() -> None:
    rows = [{'status': ' Ativo '}, {'status': 'Inativo'}]
    f = ColumnEquals(column='status', equals='Ativo')
    assert filter_rows(rows, f) == [{'status': ' Ativo '}]


def test_filter_rows_column_not_equals() -> None:
    rows = [{'status': ' Ativo '}, {'status': 'Inativo'}]
    f = ColumnNotEquals(column='status', not_equals='Ativo')
    assert filter_rows(rows, f) == [{'status': 'Inativo'}]


def test_filter_rows_column_contains() -> None:
    rows = [{'name': 'alpha_test'}, {'name': 'beta'}]
    f = ColumnContains(column='name', contains='test')
    assert filter_rows(rows, f) == [{'name': 'alpha_test'}]


def test_filter_rows_column_in() -> None:
    rows = [{'cat': ' A '}, {'cat': 'B'}, {'cat': 'C'}]
    f = ColumnIn(column='cat', in_values=['A', 'B'])
    assert filter_rows(rows, f) == [{'cat': ' A '}, {'cat': 'B'}]


def test_filter_rows_duration_at_most() -> None:
    rows = [
        {'espera': '00:01:30'},
        {'espera': '00:05:00'},
        {'espera': 'invalid'},
    ]
    f = DurationAtMost(column='espera', max_seconds=120)
    assert filter_rows(rows, f) == [{'espera': '00:01:30'}]


def test_matches_fallback() -> None:
    row = {'status': 'Ativo'}
    f = ColumnEquals(column='status', equals='Ativo')
    assert _matches(row, f) is True

    f_not = ColumnNotEquals(column='status', not_equals='Ativo')
    assert _matches(row, f_not) is False

    f_in = ColumnIn(column='status', in_values=['Ativo'])
    assert _matches(row, f_in) is True

    f_contains = ColumnContains(column='status', contains='Ati')
    assert _matches(row, f_contains) is True

    row_dur = {'espera': '00:01:00'}
    f_dur = DurationAtMost(column='espera', max_seconds=120)
    assert _matches(row_dur, f_dur) is True
