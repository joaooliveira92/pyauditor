"""Tests for dataset row filtering and duration parsing in engine strategies."""

from pyauditor.config.models import (
    ColumnContains,
    ColumnEquals,
    ColumnIn,
    ColumnNotEquals,
    DurationAtMost,
)
from pyauditor.engine.strategies._filters import (
    _matches,
    _parse_duration_seconds,
    filter_rows,
)


def test_filter_rows_none_or_empty() -> None:
    rows = [{'A': '1'}]
    assert filter_rows(rows, None) == rows
    assert filter_rows([], ColumnEquals(column='A', equals='1')) == []


def test_filter_column_equals() -> None:
    rows = [
        {'STATUS': 'Concluído'},
        {'STATUS': ' Concluído '},
        {'STATUS': 'Pendente'},
        {'OTHER': 'Concluído'},
    ]
    flt = ColumnEquals(column='STATUS', equals='Concluído')
    res = filter_rows(rows, flt)
    assert len(res) == 2
    assert res[0]['STATUS'] == 'Concluído'
    assert res[1]['STATUS'] == ' Concluído '
    assert _matches(rows[0], flt) is True
    assert _matches(rows[2], flt) is False


def test_filter_column_not_equals() -> None:
    rows = [
        {'STATUS': 'Concluído'},
        {'STATUS': 'Pendente'},
        {'STATUS': ' Cancelado '},
    ]
    flt = ColumnNotEquals(column='STATUS', not_equals='Concluído')
    res = filter_rows(rows, flt)
    assert len(res) == 2
    assert [r['STATUS'] for r in res] == ['Pendente', ' Cancelado ']
    assert _matches(rows[0], flt) is False
    assert _matches(rows[1], flt) is True


def test_filter_column_contains() -> None:
    rows = [
        {'MSG': 'Erro de timeout no servidor'},
        {'MSG': 'Sucesso na requisição'},
        {'OTHER': 'timeout'},
    ]
    flt = ColumnContains(column='MSG', contains='timeout')
    res = filter_rows(rows, flt)
    assert len(res) == 1
    assert res[0]['MSG'] == 'Erro de timeout no servidor'
    assert _matches(rows[0], flt) is True
    assert _matches(rows[1], flt) is False


def test_filter_column_in() -> None:
    rows = [
        {'FASE': 'Fase 1'},
        {'FASE': 'Fase 2 '},
        {'FASE': 'Fase 3'},
        {'FASE': 'Fase 4'},
    ]
    flt = ColumnIn(column='FASE', in_values=['Fase 1', 'Fase 2'])
    res = filter_rows(rows, flt)
    assert len(res) == 2
    assert [r['FASE'] for r in res] == ['Fase 1', 'Fase 2 ']
    assert _matches(rows[0], flt) is True
    assert _matches(rows[2], flt) is False


def test_filter_duration_at_most() -> None:
    rows = [
        {'ESPERA': '00:01:30'},  # 90s
        {'ESPERA': '00:02:00'},  # 120s
        {'ESPERA': '00:05:00'},  # 300s
        {'ESPERA': 'invalido'},
        {'ESPERA': '00:02'},
    ]
    flt = DurationAtMost(column='ESPERA', max_seconds=120)
    res = filter_rows(rows, flt)
    assert len(res) == 2
    assert [r['ESPERA'] for r in res] == ['00:01:30', '00:02:00']
    assert _matches(rows[0], flt) is True
    assert _matches(rows[2], flt) is False
    assert _matches(rows[3], flt) is False


def test_parse_duration_seconds() -> None:
    assert _parse_duration_seconds('01:00:00') == 3600
    assert _parse_duration_seconds(' 00:02:30 ') == 150
    assert _parse_duration_seconds('') is None
    assert _parse_duration_seconds('00:00') is None
    assert _parse_duration_seconds('00:00:00:00') is None
    assert _parse_duration_seconds('00:xx:00') is None
