import json
import sys
from io import StringIO

from loguru import logger as loguru_logger

from pyauditor.logging import log_event, logger, resolve_log_level, setup_logging


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


def test_resolve_log_level_verbosity_and_explicit() -> None:
    assert resolve_log_level(0, None) == "INFO"
    assert resolve_log_level(1, None) == "DEBUG"
    assert resolve_log_level(2, None) == "DEBUG"
    # `--log-level` explícito prevalece sobre `-v` (ticket 05 Q9).
    assert resolve_log_level(0, "WARNING") == "WARNING"
    assert resolve_log_level(2, "ERROR") == "ERROR"
    # valor inválido cae a INFO
    assert resolve_log_level(1, "NOPE") == "INFO"


def test_log_event_texto_carrega_contexto() -> None:
    buf = StringIO()
    setup_logging(sink=buf, level="INFO")
    log_event("indicator_measured", "indicador apurado", "INFO", orgao="MinC", codigo="INMS-1.1")
    setup_logging(sink=sys.stderr, level="INFO")
    out = buf.getvalue()
    assert "indicador apurado" in out
    assert "orgao=MinC" in out
    assert "codigo=INMS-1.1" in out


def test_log_event_omite_none() -> None:
    buf = StringIO()
    setup_logging(sink=buf, level="INFO")
    log_event("x", "v", "INFO", orgao="A", rom_path=None)
    setup_logging(sink=sys.stderr, level="INFO")
    out = buf.getvalue()
    assert "orgao=A" in out
    assert "rom_path=" not in out  # None omitido


def test_log_format_json_estructura_evento() -> None:
    buf = StringIO()
    setup_logging(sink=buf, json_format=True, verbose=1)
    log_event("indicator_measured", "indicador apurado", "INFO", orgao="MinC", status="conforme")
    setup_logging(sink=sys.stderr, level="INFO")
    payload = json.loads(buf.getvalue().splitlines()[0])
    # formato loguru `serialize=True`: `record.extra` tem event + contexto.
    assert payload["record"]["extra"]["event"] == "indicator_measured"
    assert payload["record"]["extra"]["orgao"] == "MinC"
    assert payload["record"]["extra"]["status"] == "conforme"
    assert payload["record"]["level"]["name"] == "INFO"
