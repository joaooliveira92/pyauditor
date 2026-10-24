"""Tests for dataset row filtering in pyauditor.engine.strategies._filters."""

from typing import cast

import pytest

from pyauditor.config.models import (
    ColumnContains,
    ColumnEquals,
    ColumnIn,
    ColumnNotEquals,
    DurationAtMost,
    Filter,
)
from pyauditor.engine.strategies._filters import (
    _build_predicate,
    _matches,
    filter_rows,
)


def test_filter_rows_none_filter() -> None:
    rows = [{'colA': 'val1'}, {'colA': 'val2'}]
    assert filter_rows(rows, None) == rows


def test_filter_rows_empty_rows() -> None:
    filter_eq = ColumnEquals(column='colA', equals='val1')
    assert filter_rows([], filter_eq) == []


def test_filter_rows_column_equals() -> None:
    filter_eq = ColumnEquals(column='status', equals='OK')
    rows = [
        {'status': ' OK '},
        {'status': 'NOK'},
        {'other': 'val'},
    ]
    retained = filter_rows(rows, filter_eq)
    assert len(retained) == 1
    assert retained[0]['status'] == ' OK '


def test_filter_rows_column_not_equals() -> None:
    filter_neq = ColumnNotEquals(column='status', not_equals='REJECTED')
    rows = [
        {'status': 'APPROVED'},
        {'status': 'REJECTED'},
        {'status': ' REJECTED '},
        {'other': 'val'},
    ]
    retained = filter_rows(rows, filter_neq)
    assert len(retained) == 2
    assert [r.get('status') for r in retained] == ['APPROVED', None]


def test_filter_rows_column_contains() -> None:
    filter_contains = ColumnContains(column='msg', contains='error')
    rows = [
        {'msg': 'fatal error occurred'},
        {'msg': 'success'},
        {'msg': 'ERRORS in log'},
    ]
    retained = filter_rows(rows, filter_contains)
    assert len(retained) == 1
    assert retained[0]['msg'] == 'fatal error occurred'


def test_filter_rows_column_in() -> None:
    filter_in = ColumnIn(column='code', in_values=['200', '201', '202'])
    rows = [
        {'code': '200'},
        {'code': ' 201 '},
        {'code': '404'},
        {'code': '500'},
    ]
    retained = filter_rows(rows, filter_in)
    assert len(retained) == 2


def test_filter_rows_duration_at_most() -> None:
    filter_dur = DurationAtMost(column='espera', max_seconds=300)
    rows = [
        {'espera': '0:03:00'},  # 180s
        {'espera': '0:05:00'},  # 300s
        {'espera': '0:05:01'},  # 301s
        {'espera': 'invalid'},
    ]
    retained = filter_rows(rows, filter_dur)
    assert len(retained) == 2


def test_matches_and_build_predicate() -> None:
    filter_eq = ColumnEquals(column='colA', equals='test')
    row = {'colA': 'test'}
    assert _matches(row, filter_eq) is True
    pred = _build_predicate(filter_eq)
    assert pred(row) is True


def test_unsupported_filter_raises_type_error() -> None:
    class DummyFilter:
        column = 'colA'

    with pytest.raises(TypeError, match='Filtro não suportado'):
        _build_predicate(cast(Filter, DummyFilter()))
