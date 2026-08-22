from pyauditor.engine.strategies._numbers import as_float, parse_decimal


def test_parse_decimal_handles_pt_br_comma_separator() -> None:
    assert parse_decimal('99,451') == 99.451


def test_parse_decimal_handles_dot_separator() -> None:
    assert parse_decimal('99.451') == 99.451


def test_parse_decimal_returns_nan_for_unparseable_input() -> None:
    import math

    assert math.isnan(parse_decimal('not a number'))


def test_as_float_rejects_bool() -> None:
    assert as_float(True) is None
    assert as_float(False) is None


def test_as_float_accepts_numbers() -> None:
    assert as_float(1) == 1.0
    assert as_float(1.5) == 1.5


def test_as_float_rejects_non_numeric() -> None:
    assert as_float('1.5') is None
    assert as_float(None) is None
