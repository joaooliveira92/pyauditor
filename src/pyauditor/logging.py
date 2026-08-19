"""Shared Loguru logger for the pyauditor pipeline.

Every CLI run also writes a file log (timestamped, next to the run's outputs)
so the user can trace errors after the console output is gone — the console
keeps only the live INFO/ERROR stream.
"""

import sys
from pathlib import Path
from typing import Final, TextIO

from loguru import logger

__all__: Final[tuple[str, ...]] = ("logger", "setup_logging")

_LOG_FORMAT: Final[str] = "{time:HH:mm:ss} | {level: <8} | {message}"
_FILE_LOG_FORMAT: Final[str] = (
    "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} | {message}"
)
_LOG_LEVEL: Final[str] = "INFO"


def setup_logging(
    *,
    sink: TextIO | str | Path = sys.stderr,
    level: str = _LOG_LEVEL,
    format_: str = _LOG_FORMAT,
    log_path: TextIO | str | Path | None = None,
) -> int:
    """Configure the shared logger, replacing any previously configured sinks.

    Safe to call repeatedly (e.g. once per test) — always removes prior
    handlers first, so sinks never accumulate. When *log_path* is given, the
    same records also go to that file (created if needed).

    Returns the console handler id from `loguru.logger.add`.
    """
    logger.remove()
    console_handler_id: int = logger.add(sink, level=level, format=format_)
    if log_path is not None:
        if isinstance(log_path, (str, Path)):
            path = Path(log_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            logger.add(
                path,
                level=level,
                format=_FILE_LOG_FORMAT,
                encoding="utf-8",
                enqueue=False,
            )
        else:
            # file-like sink (e.g. StringIO in tests) — no path to create
            logger.add(log_path, level=level, format=_FILE_LOG_FORMAT)
    return console_handler_id


# Configure on import; re-entrant for tests via setup_logging().
setup_logging()
