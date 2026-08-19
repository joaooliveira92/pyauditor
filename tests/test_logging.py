import sys

from loguru import logger as loguru_logger

from pyauditor.logging import logger, setup_logging


def test_logger_is_the_shared_loguru_instance() -> None:
    assert logger is loguru_logger


def test_setup_logging_returns_handler_id() -> None:
    handler_id = setup_logging(sink=sys.stderr, level="INFO")
    assert isinstance(handler_id, int)
    assert handler_id >= 0
    # idempotent — second call must not duplicate handlers
    handler_id2 = setup_logging(sink=sys.stderr, level="DEBUG")
    assert isinstance(handler_id2, int)


def test_logger_methods_work() -> None:
    logger.info("hello {}", "world")
    logger.error("boom {}", 123)
    logger.debug("debug")


def test_all_exports() -> None:
    import pyauditor.logging as m

    assert "logger" in m.__all__
    assert "setup_logging" in m.__all__
