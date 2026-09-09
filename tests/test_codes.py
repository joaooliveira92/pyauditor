from pyauditor.codes import (
    contractual_sort_key,
    format_inms_code,
    format_inms_code_numeric,
    parse_inms_code,
)


def test_format_inms_code_zero_pads_minor_version() -> None:
    assert format_inms_code('INMS 1.1') == 'INMS 1.01'
    assert format_inms_code('INMS 1.9') == 'INMS 1.09'
    assert format_inms_code('INMS 1.10') == 'INMS 1.10'
    assert format_inms_code('INMS 1.14') == 'INMS 1.14'


def test_format_inms_code_is_idempotent() -> None:
    assert format_inms_code('INMS 1.01') == 'INMS 1.01'
    assert format_inms_code('INMS 1.10') == 'INMS 1.10'


def test_format_inms_code_passes_non_matching_codes_through() -> None:
    assert format_inms_code('INMS TEST') == 'INMS TEST'
    assert format_inms_code('') == ''


def test_format_inms_code_numeric() -> None:
    assert format_inms_code_numeric('INMS 1.1') == '1.01'
    assert format_inms_code_numeric('INMS 1.9') == '1.09'
    assert format_inms_code_numeric('INMS 1.10') == '1.10'
    assert format_inms_code_numeric('INVALID') == 'INVALID'


def test_parse_inms_code() -> None:
    assert parse_inms_code('1.02') == 'INMS 1.02'
    assert parse_inms_code('INMS 1.02') == 'INMS 1.02'
    assert parse_inms_code('INMS 1.2') == 'INMS 1.02'


def test_contractual_sort_key() -> None:
    codes = ['INMS 1.10', 'INMS 1.2', 'INMS 1.1', 'OTHER']
    sorted_codes = sorted(codes, key=contractual_sort_key)
    assert sorted_codes == ['INMS 1.1', 'INMS 1.2', 'INMS 1.10', 'OTHER']


def test_lru_cache_behavior() -> None:
    format_inms_code_numeric.cache_clear()
    parse_inms_code.cache_clear()
    contractual_sort_key.cache_clear()

    _ = format_inms_code_numeric('INMS 1.1')
    _ = format_inms_code_numeric('INMS 1.1')
    assert format_inms_code_numeric.cache_info().hits >= 1

    _ = parse_inms_code('1.01')
    _ = parse_inms_code('1.01')
    assert parse_inms_code.cache_info().hits >= 1

    _ = contractual_sort_key('INMS 1.1')
    _ = contractual_sort_key('INMS 1.1')
    assert contractual_sort_key.cache_info().hits >= 1
