from pyauditor.logging import logger


def test_logger_is_importable() -> None:
    assert logger is not None
