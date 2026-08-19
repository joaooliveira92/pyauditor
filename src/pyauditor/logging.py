"""Shared Loguru logger for the pyauditor pipeline."""

import sys
from pathlib import Path
from typing import Final, TextIO

from loguru import logger

__all__: Final[tuple[str, ...]] = ("logger", "setup_logging")

_LOG_FORMAT: Final[str] = "{time:HH:mm:ss} | {level: <8} | {message}"
_LOG_LEVEL: Final[str] = "INFO"


def setup_logging(
    *,
    sink: TextIO | str | Path = sys.stderr,
    level: str = _LOG_LEVEL,
    format_: str = _LOG_FORMAT,
) -> int:
    """Configure the shared logger, replacing any previously configured sinks.

    Safe to call repeatedly (e.g. once per test) — always removes prior
    handlers first, so sinks never accumulate.

    Returns the handler id from `loguru.logger.add`.
    """
    logger.remove()
    handler_id: int = logger.add(sink, level=level, format=format_)
    return handler_id


# Configure on import; re-entrant for tests via setup_logging().
setup_logging()
