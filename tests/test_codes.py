from pyauditor.codes import format_inms_code


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
