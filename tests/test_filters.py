"""Testes unitários para a filtragem de linhas de datasets e parsing de
duração.
"""

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


def test_filter_rows_returns_original_when_filter_is_none() -> None:
    rows = [{'A': '1'}, {'A': '2'}]
    assert filter_rows(rows, None) == rows


def test_filter_rows_returns_empty_when_rows_empty() -> None:
    f = ColumnEquals(column='STATUS', equals='OK')
    assert filter_rows([], f) == []


def test_filter_rows_column_equals() -> None:
    rows = [
        {'STATUS': ' FECHADO '},
        {'STATUS': 'ABERTO'},
        {'OTHER': 'FECHADO'},
    ]
    f = ColumnEquals(column='STATUS', equals='FECHADO')
    filtered = filter_rows(rows, f)
    assert len(filtered) == 1
    assert filtered[0]['STATUS'] == ' FECHADO '


def test_filter_rows_column_not_equals() -> None:
    rows = [
        {'STATUS': 'FECHADO'},
        {'STATUS': 'ABERTO'},
    ]
    f = ColumnNotEquals(column='STATUS', not_equals='FECHADO')
    filtered = filter_rows(rows, f)
    assert len(filtered) == 1
    assert filtered[0]['STATUS'] == 'ABERTO'


def test_filter_rows_column_contains() -> None:
    rows = [
        {'DESC': 'Falha na rede local'},
        {'DESC': 'Sucesso no processamento'},
    ]
    f = ColumnContains(column='DESC', contains='rede')
    filtered = filter_rows(rows, f)
    assert len(filtered) == 1
    assert 'rede' in filtered[0]['DESC']


def test_filter_rows_column_in() -> None:
    rows = [
        {'STATUS': 'RESOLVIDO'},
        {'STATUS': 'FECHADO'},
        {'STATUS': 'ABERTO'},
    ]
    f = ColumnIn(column='STATUS', in_values=['RESOLVIDO', 'FECHADO'])
    filtered = filter_rows(rows, f)
    assert len(filtered) == 2
    assert {r['STATUS'] for r in filtered} == {'RESOLVIDO', 'FECHADO'}


def test_filter_rows_duration_at_most() -> None:
    rows = [
        {'ESPERA': '00:01:30'},  # 90s
        {'ESPERA': '00:05:00'},  # 300s
        {'ESPERA': 'invalid'},
    ]
    f = DurationAtMost(column='ESPERA', max_seconds=120)
    filtered = filter_rows(rows, f)
    assert len(filtered) == 1
    assert filtered[0]['ESPERA'] == '00:01:30'


def test_parse_duration_seconds() -> None:
    assert _parse_duration_seconds('01:20:30') == 4830
    assert _parse_duration_seconds('00:00:00') == 0
    assert _parse_duration_seconds('invalid') is None
    assert _parse_duration_seconds('12:34') is None
    assert _parse_duration_seconds('1:2:3:4') is None
    assert _parse_duration_seconds('-1:00:00') is None
