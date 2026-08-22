"""Configure structured logging and pipeline observability.

The module exposes the shared Loguru logger and the functions used to configure
logging at application startup.

Logging and command output are separate surfaces:

- logs are written to stderr and, optionally, a readable log file;
- the completion summary is written independently to stdout;
- JSON summary output does not change the logging format;
- JSON log output applies only to the configured stream sink.

Verbosity controls event detail:

- verbosity 0 emits INFO and higher-severity events;
- ``-v`` enables DEBUG events with detail level 1, such as one event per
  measured indicator;
- ``-vv`` additionally enables DEBUG events with detail level 2, such as
  input-reading, validation, and calculation details.

``--log-level`` takes precedence over verbosity. A programmatic ``level``
argument is used when no explicit CLI level is supplied and verbosity is zero.

When JSON logging is enabled, each stream record is emitted as exactly one
flat JSON object with this stable core schema:

    {
        "time": "2026-08-22T03:48:00.000000+00:00",
        "level": "INFO",
        "event": "indicator_measured",
        "message": "indicador apurado",
        "...context": "..."
    }

The optional file sink always remains human-readable.

This module performs no configuration during import. Application entry points
must call :func:`setup_logging` after parsing command-line options.
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final, TextIO, cast

from loguru import logger

from pyauditor.log_contract import (
    format_text_value,
    normalize_context,
    normalize_level,
    validate_detail,
    validate_event,
    validate_single_line_text,
)
from pyauditor.log_json_sink import FlatJsonSink

__all__: Final[tuple[str, ...]] = (
    'LoggingHandlers',
    'log_event',
    'logger',
    'resolve_log_level',
    'setup_logging',
)

type Sink = TextIO | str | Path

_DEFAULT_LOG_LEVEL: Final[str] = 'INFO'
_DEFAULT_DETAIL_LEVEL: Final[int] = 0
_MAX_DETAIL_LEVEL: Final[int] = 2

_STREAM_LOG_FORMAT: Final[str] = '{time:HH:mm:ss} | {level: <8} | {message}'
_FILE_LOG_FORMAT: Final[str] = (
    '{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{line} | {message}'
)

_LOG_RETENTION: Final[int] = 5


@dataclass(frozen=True, slots=True)
class LoggingHandlers:
    """Contain handler identifiers created by :func:`setup_logging`.

    Attributes:
        stream: Handler used for stderr or another stream sink.
        file: Optional handler used for the readable log file.
    """

    stream: int
    file: int | None = None


def resolve_log_level(
    verbosity: int,
    explicit: str | None,
    *,
    default: str = _DEFAULT_LOG_LEVEL,
) -> str:
    """Resolve the effective Loguru severity threshold.

    Precedence is:

    1. ``explicit``, when supplied;
    2. ``DEBUG`` when verbosity is one or greater;
    3. ``default``.

    Verbosity values greater than two are accepted and treated as two. The
    detail filter still exposes only the supported detail levels zero, one,
    and two.

    Args:
        verbosity: Number of ``-v`` flags.
        explicit: Optional level supplied through ``--log-level``.
        default: Programmatic fallback level.

    Returns:
        A normalized supported Loguru level.

    Raises:
        TypeError: If verbosity is not a non-boolean integer or a level value
            is not a string.
        ValueError: If verbosity is negative or a level is unsupported.
    """
    normalized_verbosity = _validate_verbosity(verbosity)
    normalized_default = normalize_level(
        default,
        field='default',
    )

    if explicit is not None:
        return normalize_level(
            explicit,
            field='explicit',
        )

    if normalized_verbosity > 0:
        return 'DEBUG'

    return normalized_default


def log_event(
    event: str,
    verb: str,
    level: str = _DEFAULT_LOG_LEVEL,
    *,
    detail: int = _DEFAULT_DETAIL_LEVEL,
    **context: object,
) -> None:
    """Emit a structured pipeline event.

    ``event`` is the stable machine-readable identifier. ``verb`` is the
    concise human-readable message. Context values are available as root
    fields in JSON logs and as ``key=value`` pairs in readable logs.

    Detail levels are independent from severity:

    - detail 0 is used for normal operational events;
    - detail 1 is used for per-indicator DEBUG events;
    - detail 2 is used for extended reading, validation, and calculation
      diagnostics.

    Context values equal to ``None`` are omitted. Context keys that conflict
    with the JSON schema, appear sensitive, or do not form valid identifiers
    are rejected.

    Args:
        event: Stable snake_case event identifier.
        verb: Human-readable single-line event description.
        level: Supported Loguru severity.
        detail: Required verbosity detail level from zero through two.
        **context: Non-sensitive structured event fields.

    Raises:
        TypeError: If event, verb, level, detail, a context key, or a context
            value violates its runtime type contract.
        ValueError: If identifiers, severity, detail, or context are invalid.
    """
    normalized_event = validate_event(event)
    normalized_verb = validate_single_line_text(
        verb,
        field='verb',
    )
    normalized_level = normalize_level(
        level,
        field='level',
    )
    normalized_detail = validate_detail(detail)
    normalized_context = normalize_context(context)

    readable_context = ' '.join(
        f'{key}={format_text_value(value)}'
        for key, value in normalized_context.items()
    )
    readable_message = (
        f'{normalized_verb} | {readable_context}'
        if readable_context
        else normalized_verb
    )

    logger.bind(
        event=normalized_event,
        event_message=normalized_verb,
        detail=normalized_detail,
        **normalized_context,
    ).log(
        normalized_level,
        readable_message,
    )


def setup_logging(
    *,
    sink: Sink = sys.stderr,
    level: str = _DEFAULT_LOG_LEVEL,
    format_: str = _STREAM_LOG_FORMAT,
    log_path: Sink | None = None,
    verbose: int = 0,
    log_level_explicit: str | None = None,
    json_format: bool = False,
) -> LoggingHandlers:
    """Replace existing handlers with validated pipeline logging handlers.

    The function validates predictable configuration errors before modifying
    the global logger. If adding one of the new handlers fails, handlers
    created by this call are removed before the exception is propagated.

    The stream handler uses a detail filter to distinguish ``-v`` from
    ``-vv``. The optional readable file uses the same effective severity and
    detail policy.

    JSON mode requires a writable file-like stream. Paths are rejected for the
    JSON stream because JSON logging is intended for stderr or another
    automation-controlled stream. The optional file log remains readable text.

    ``backtrace`` and ``diagnose`` are disabled to avoid unexpectedly exposing
    local variables or excessive exception context.

    Args:
        sink: Stream or path used by the primary log handler.
        level: Programmatic fallback severity threshold.
        format_: Human-readable format used by the primary stream.
        log_path: Optional readable file or stream sink.
        verbose: Number of ``-v`` flags.
        log_level_explicit: Optional CLI severity override.
        json_format: Whether the primary stream uses flat one-line JSON.

    Returns:
        Identifiers for the installed stream and optional file handlers.

    Raises:
        TypeError: If configuration values have invalid runtime types.
        ValueError: If severity, verbosity, format, or sink configuration is
            unsupported.
        OSError: If a log directory or file cannot be created.
    """
    normalized_verbosity = _validate_verbosity(verbose)
    effective_level = resolve_log_level(
        normalized_verbosity,
        log_level_explicit,
        default=level,
    )
    maximum_detail = min(
        normalized_verbosity,
        _MAX_DETAIL_LEVEL,
    )

    if not format_:
        raise ValueError('format_ must not be empty.')

    if type(json_format) is not bool:
        raise TypeError(
            f'json_format must be bool, received {type(json_format).__name__}.'
        )

    if json_format and isinstance(sink, (str, Path)):
        raise ValueError(
            'JSON log format requires a writable file-like stream, '
            'such as sys.stderr.'
        )

    _validate_sink(sink, field='sink')

    if log_path is not None:
        _validate_sink(log_path, field='log_path')

    if isinstance(log_path, (str, Path)):
        Path(log_path).parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    detail_filter = _build_detail_filter(
        maximum_detail=maximum_detail,
    )
    json_sink = FlatJsonSink(cast(TextIO, sink)) if json_format else None

    logger.remove()

    stream_handler_id: int | None = None
    file_handler_id: int | None = None

    try:
        if json_sink is not None:
            stream_handler_id = logger.add(
                json_sink,
                level=effective_level,
                filter=detail_filter,
                backtrace=False,
                diagnose=False,
                enqueue=False,
                catch=False,
            )
        else:
            stream_handler_id = logger.add(
                sink,
                level=effective_level,
                filter=detail_filter,
                format=format_,
                backtrace=False,
                diagnose=False,
                enqueue=False,
                catch=False,
            )

        if log_path is not None:
            if isinstance(log_path, (str, Path)):
                file_handler_id = logger.add(
                    log_path,
                    level=effective_level,
                    filter=detail_filter,
                    format=_FILE_LOG_FORMAT,
                    backtrace=False,
                    diagnose=False,
                    enqueue=False,
                    catch=False,
                    encoding='utf-8',
                    retention=_LOG_RETENTION,
                )
            else:
                file_handler_id = logger.add(
                    log_path,
                    level=effective_level,
                    filter=detail_filter,
                    format=_FILE_LOG_FORMAT,
                    backtrace=False,
                    diagnose=False,
                    enqueue=False,
                    catch=False,
                )
    except Exception:
        if file_handler_id is not None:
            logger.remove(file_handler_id)

        if stream_handler_id is not None:
            logger.remove(stream_handler_id)

        raise

    return LoggingHandlers(
        stream=stream_handler_id,
        file=file_handler_id,
    )


def _build_detail_filter(
    *,
    maximum_detail: int,
) -> Callable[[Mapping[str, object]], bool]:
    """Build a Loguru filter for the configured detail depth."""

    def filter_record(record: Mapping[str, object]) -> bool:
        extra = record.get('extra', {})
        if not isinstance(extra, Mapping):
            return True

        extra_values = cast(Mapping[str, object], extra)
        detail = extra_values.get(
            'detail',
            _DEFAULT_DETAIL_LEVEL,
        )
        if isinstance(detail, bool) or not isinstance(detail, int):
            return False

        return detail <= maximum_detail

    return filter_record


def _validate_verbosity(verbosity: int) -> int:
    """Validate and normalize a CLI verbosity count."""
    if type(verbosity) is not int:
        raise TypeError(
            'verbosity must be an integer, '
            f'received {type(verbosity).__name__}.'
        )

    if verbosity < 0:
        raise ValueError(
            f'verbosity must not be negative, received {verbosity}.'
        )

    return min(verbosity, _MAX_DETAIL_LEVEL)


def _validate_sink(
    sink: Sink,
    *,
    field: str,
) -> None:
    """Validate a supported Loguru sink value."""
    if isinstance(sink, (str, Path)):
        if not str(sink):
            raise ValueError(f'{field} path must not be empty.')
        return

    if not callable(getattr(sink, 'write', None)):
        raise TypeError(
            f'{field} must be a path or writable text stream, '
            f'received {type(sink).__name__}.'
        )
