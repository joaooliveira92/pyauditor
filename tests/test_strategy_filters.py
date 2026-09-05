"""Testes para a função de filtragem de linhas `filter_rows` e
`_parse_duration_seconds`.
"""

from __future__ import annotations

from pyauditor.config.models import (
    ColumnContains,
    ColumnEquals,
    ColumnIn,
    ColumnNotEquals,
    DurationAtMost,
)
from pyauditor.engine.strategies._filters import (
    _parse_duration_seconds,
    filter_rows,
)


def test_filter_rows_none_returns_all_rows() -> None:
    rows = [{'col': 'val1'}, {'col': 'val2'}]
    assert filter_rows(rows, None) == rows


def test_filter_rows_empty_list() -> None:
    rows: list[dict[str, str]] = []
    assert filter_rows(rows, ColumnEquals(column='col', equals='val1')) == []


def test_filter_rows_column_equals() -> None:
    rows = [
        {'col': ' val1 '},
        {'col': 'val2'},
        {'other': 'val1'},
    ]
    f = ColumnEquals(column='col', equals='val1')
    res = filter_rows(rows, f)
    assert len(res) == 1
    assert res[0]['col'] == ' val1 '


def test_filter_rows_column_not_equals() -> None:
    rows = [
        {'col': 'val1'},
        {'col': 'val2'},
        {'col': 'val1'},
    ]
    f = ColumnNotEquals(column='col', not_equals='val1')
    res = filter_rows(rows, f)
    assert len(res) == 1
    assert res[0]['col'] == 'val2'


def test_filter_rows_column_contains() -> None:
    rows = [
        {'col': 'hello world'},
        {'col': 'goodbye'},
    ]
    f = ColumnContains(column='col', contains='world')
    res = filter_rows(rows, f)
    assert len(res) == 1
    assert res[0]['col'] == 'hello world'


def test_filter_rows_column_in() -> None:
    rows = [
        {'col': 'a'},
        {'col': 'b'},
        {'col': 'c'},
    ]
    f = ColumnIn(column='col', in_values=['a', 'c'])
    res = filter_rows(rows, f)
    assert len(res) == 2
    assert [r['col'] for r in res] == ['a', 'c']


def test_filter_rows_duration_at_most() -> None:
    rows = [
        {'espera': '0:00:30'},
        {'espera': '0:01:00'},
        {'espera': '0:02:00'},
        {'espera': 'invalid'},
    ]
    f = DurationAtMost(column='espera', max_seconds=60)
    res = filter_rows(rows, f)
    assert len(res) == 2
    assert [r['espera'] for r in res] == ['0:00:30', '0:01:00']


def test_parse_duration_seconds() -> None:
    assert _parse_duration_seconds('0:00:00') == 0
    assert _parse_duration_seconds('1:30:15') == 5415
    assert _parse_duration_seconds('invalid') is None
    assert _parse_duration_seconds('1:2') is None
    assert _parse_duration_seconds('a:b:c') is None
