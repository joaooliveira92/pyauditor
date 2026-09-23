from pyauditor.config.models import (
    ColumnContains,
    ColumnEquals,
    ColumnIn,
    ColumnNotEquals,
    DurationAtMost,
)
from pyauditor.engine.strategies._filters import filter_rows


def test_filter_rows_none_filter() -> None:
    rows = [{'A': '1'}, {'A': '2'}]
    assert filter_rows(rows, None) == rows


def test_filter_rows_empty_rows() -> None:
    flt = ColumnEquals(column='STATUS', equals='OK')
    assert filter_rows([], flt) == []


def test_filter_rows_column_equals() -> None:
    rows = [
        {'STATUS': ' OK '},
        {'STATUS': 'NOK'},
        {'OTHER': 'OK'},
    ]
    flt = ColumnEquals(column='STATUS', equals='OK')
    res = filter_rows(rows, flt)
    assert len(res) == 1
    assert res[0]['STATUS'] == ' OK '


def test_filter_rows_column_not_equals() -> None:
    rows = [
        {'STATUS': ' OK '},
        {'STATUS': 'NOK'},
        {'OTHER': 'OK'},
    ]
    flt = ColumnNotEquals(column='STATUS', not_equals='OK')
    res = filter_rows(rows, flt)
    assert len(res) == 2
    assert res[0]['STATUS'] == 'NOK'
    assert res[1]['OTHER'] == 'OK'


def test_filter_rows_column_contains() -> None:
    rows = [
        {'MSG': 'Error: timeout'},
        {'MSG': 'Success: done'},
        {'MSG': 'Warn: timeout approaching'},
    ]
    flt = ColumnContains(column='MSG', contains='timeout')
    res = filter_rows(rows, flt)
    assert len(res) == 2
    assert res[0]['MSG'] == 'Error: timeout'
    assert res[1]['MSG'] == 'Warn: timeout approaching'


def test_filter_rows_column_in() -> None:
    rows = [
        {'STATE': ' SP '},
        {'STATE': 'RJ'},
        {'STATE': 'MG'},
        {'STATE': 'RS'},
    ]
    flt = ColumnIn(column='STATE', in_values=['SP', 'RJ'])
    res = filter_rows(rows, flt)
    assert len(res) == 2
    assert res[0]['STATE'] == ' SP '
    assert res[1]['STATE'] == 'RJ'


def test_filter_rows_duration_at_most() -> None:
    rows = [
        {'ESPERA': '0:01:30'},  # 90s
        {'ESPERA': '0:05:00'},  # 300s
        {'ESPERA': '0:02:00'},  # 120s
        {'ESPERA': 'invalid'},
        {'OTHER': '0:00:30'},
    ]
    flt = DurationAtMost(column='ESPERA', max_seconds=120)
    res = filter_rows(rows, flt)
    assert len(res) == 2
    assert res[0]['ESPERA'] == '0:01:30'
    assert res[1]['ESPERA'] == '0:02:00'
