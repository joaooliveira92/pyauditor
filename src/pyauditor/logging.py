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

import json
import re
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from math import isfinite
from pathlib import Path
from threading import Lock
from typing import Final, TextIO, TypeAlias, cast

from loguru import logger

__all__: Final[tuple[str, ...]] = (
    "LoggingHandlers",
    "log_event",
    "logger",
    "resolve_log_level",
    "setup_logging",
)

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
Sink: TypeAlias = TextIO | str | Path

_DEFAULT_LOG_LEVEL: Final[str] = "INFO"
_SUPPORTED_LEVELS: Final[frozenset[str]] = frozenset(
    {
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    }
)

_STREAM_LOG_FORMAT: Final[str] = (
    "{time:HH:mm:ss} | {level: <8} | {message}"
)
_FILE_LOG_FORMAT: Final[str] = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
    "{level: <8} | {name}:{line} | {message}"
)

_EVENT_RE: Final[re.Pattern[str]] = re.compile(
    r"^[a-z][a-z0-9_]*$"
)
_CONTEXT_KEY_RE: Final[re.Pattern[str]] = re.compile(
    r"^[a-zA-Z_][a-zA-Z0-9_]*$"
)

_RESERVED_CONTEXT_KEYS: Final[frozenset[str]] = frozenset(
    {
        "time",
        "level",
        "event",
        "message",
        "detail",
    }
)

_SENSITIVE_KEY_FRAGMENTS: Final[frozenset[str]] = frozenset(
    {
        "api_key",
        "authorization",
        "credential",
        "password",
        "secret",
        "token",
    }
)

_LOG_RETENTION: Final[int] = 5
_DEFAULT_DETAIL_LEVEL: Final[int] = 0
_MAX_DETAIL_LEVEL: Final[int] = 2


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
    normalized_default = _normalize_level(
        default,
        field="default",
    )

    if explicit is not None:
        return _normalize_level(
            explicit,
            field="explicit",
        )

    if normalized_verbosity > 0:
        return "DEBUG"

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
    normalized_event = _validate_event(event)
    normalized_verb = _validate_single_line_text(
        verb,
        field="verb",
    )
    normalized_level = _normalize_level(
        level,
        field="level",
    )
    normalized_detail = _validate_detail(detail)
    normalized_context = _normalize_context(context)

    readable_context = " ".join(
        f"{key}={_format_text_value(value)}"
        for key, value in normalized_context.items()
    )
    readable_message = (
        f"{normalized_verb} | {readable_context}"
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

    if not isinstance(format_, str):
        raise TypeError(
            "format_ must be a string, "
            f"received {type(format_).__name__}."
        )

    if not format_:
        raise ValueError("format_ must not be empty.")

    if not isinstance(json_format, bool):
        raise TypeError(
            "json_format must be bool, "
            f"received {type(json_format).__name__}."
        )

    if json_format and isinstance(sink, (str, Path)):
        raise ValueError(
            "JSON log format requires a writable file-like stream, "
            "such as sys.stderr."
        )

    _validate_sink(sink, field="sink")

    if log_path is not None:
        _validate_sink(log_path, field="log_path")

    if isinstance(log_path, (str, Path)):
        Path(log_path).parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    detail_filter = _build_detail_filter(
        maximum_detail=maximum_detail,
    )
    json_sink = (
        _FlatJsonSink(cast(TextIO, sink))
        if json_format
        else None
    )

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
            file_options: dict[str, object] = {
                "level": effective_level,
                "filter": detail_filter,
                "format": _FILE_LOG_FORMAT,
                "backtrace": False,
                "diagnose": False,
                "enqueue": False,
                "catch": False,
            }

            if isinstance(log_path, (str, Path)):
                file_options.update(
                    {
                        "encoding": "utf-8",
                        "retention": _LOG_RETENTION,
                    }
                )

            file_handler_id = logger.add(
                log_path,
                **file_options,
            )
    except Exception:
        if file_handler_id is not None:
            logger.remove(file_handler_id)

        if stream_handler_id is not None:
            logger.remove(stream_handler_id)

        raise

    if stream_handler_id is None:
        raise RuntimeError(
            "Logging configuration completed without a stream handler."
        )

    return LoggingHandlers(
        stream=stream_handler_id,
        file=file_handler_id,
    )


class _FlatJsonSink:
    """Write Loguru records as stable flat one-line JSON objects."""

    def __init__(self, stream: TextIO) -> None:
        """Initialize the sink with a writable text stream."""
        if not callable(getattr(stream, "write", None)):
            raise TypeError(
                "JSON log sink must provide a writable text interface."
            )

        self._stream = stream
        self._lock = Lock()

    def write(self, message: object) -> None:
        """Serialize and write one Loguru message."""
        record = getattr(message, "record", None)
        if not isinstance(record, Mapping):
            raise TypeError(
                "Loguru JSON sink received a message without a record."
            )

        extra_raw = record.get("extra", {})
        if not isinstance(extra_raw, Mapping):
            raise TypeError(
                "Loguru record extra context must be a mapping."
            )

        extra = {
            str(key): _normalize_json_value(value)
            for key, value in extra_raw.items()
            if key not in {"event_message", "detail"}
        }

        timestamp = record.get("time")
        level = record.get("level")

        event = extra_raw.get("event", "unstructured_log")
        event_message = extra_raw.get(
            "event_message",
            record.get("message", ""),
        )

        payload: dict[str, JsonValue] = {
            "time": _format_timestamp(timestamp),
            "level": _format_level(level),
            "event": _validate_event(str(event)),
            "message": _validate_single_line_text(
                str(event_message),
                field="message",
            ),
        }
        payload.update(extra)

        serialized = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
            sort_keys=False,
        )

        with self._lock:
            self._stream.write(f"{serialized}\n")
            flush = getattr(self._stream, "flush", None)
            if callable(flush):
                flush()


def _build_detail_filter(
    *,
    maximum_detail: int,
) -> Callable[[Mapping[str, object]], bool]:
    """Build a Loguru filter for the configured detail depth."""

    def filter_record(record: Mapping[str, object]) -> bool:
        extra = record.get("extra", {})
        if not isinstance(extra, Mapping):
            return True

        detail = extra.get(
            "detail",
            _DEFAULT_DETAIL_LEVEL,
        )
        if isinstance(detail, bool) or not isinstance(detail, int):
            return False

        return detail <= maximum_detail

    return filter_record


def _normalize_level(
    level: str,
    *,
    field: str,
) -> str:
    """Normalize and validate a supported severity."""
    if not isinstance(level, str):
        raise TypeError(
            f"{field} must be a string, "
            f"received {type(level).__name__}."
        )

    normalized = level.strip().upper()

    if normalized not in _SUPPORTED_LEVELS:
        raise ValueError(
            f"Unsupported {field} {level!r}; expected one of "
            f"{sorted(_SUPPORTED_LEVELS)!r}."
        )

    return normalized


def _validate_verbosity(verbosity: int) -> int:
    """Validate and normalize a CLI verbosity count."""
    if isinstance(verbosity, bool) or not isinstance(verbosity, int):
        raise TypeError(
            "verbosity must be an integer, "
            f"received {type(verbosity).__name__}."
        )

    if verbosity < 0:
        raise ValueError(
            f"verbosity must not be negative, received {verbosity}."
        )

    return min(verbosity, _MAX_DETAIL_LEVEL)


def _validate_detail(detail: int) -> int:
    """Validate an event detail level."""
    if isinstance(detail, bool) or not isinstance(detail, int):
        raise TypeError(
            "detail must be an integer, "
            f"received {type(detail).__name__}."
        )

    if not 0 <= detail <= _MAX_DETAIL_LEVEL:
        raise ValueError(
            f"detail must be between 0 and {_MAX_DETAIL_LEVEL}, "
            f"received {detail}."
        )

    return detail


def _validate_event(event: str) -> str:
    """Validate a stable event identifier."""
    if not isinstance(event, str):
        raise TypeError(
            "event must be a string, "
            f"received {type(event).__name__}."
        )

    normalized = event.strip()

    if _EVENT_RE.fullmatch(normalized) is None:
        raise ValueError(
            "event must use snake_case and match "
            f"{_EVENT_RE.pattern!r}, received {event!r}."
        )

    return normalized


def _validate_single_line_text(
    value: str,
    *,
    field: str,
) -> str:
    """Require non-empty text without line breaks."""
    if not isinstance(value, str):
        raise TypeError(
            f"{field} must be a string, "
            f"received {type(value).__name__}."
        )

    normalized = value.strip()

    if not normalized:
        raise ValueError(f"{field} must not be empty.")

    if "\n" in normalized or "\r" in normalized:
        raise ValueError(
            f"{field} must contain exactly one line."
        )

    return normalized


def _normalize_context(
    context: Mapping[str, object],
) -> dict[str, JsonValue]:
    """Validate context keys and normalize values for text and JSON sinks."""
    normalized: dict[str, JsonValue] = {}

    for key, value in context.items():
        if not isinstance(key, str):
            raise TypeError(
                "Context keys must be strings, "
                f"received {type(key).__name__}."
            )

        normalized_key = key.strip()

        if _CONTEXT_KEY_RE.fullmatch(normalized_key) is None:
            raise ValueError(
                f"Invalid context key: {key!r}."
            )

        if normalized_key in _RESERVED_CONTEXT_KEYS:
            raise ValueError(
                f"Context key {normalized_key!r} is reserved."
            )

        lowered_key = normalized_key.lower()
        if any(
            fragment in lowered_key
            for fragment in _SENSITIVE_KEY_FRAGMENTS
        ):
            raise ValueError(
                f"Context key {normalized_key!r} may contain sensitive data."
            )

        if value is None:
            continue

        normalized[normalized_key] = _normalize_json_value(
            value
        )

    return normalized


def _normalize_json_value(value: object) -> JsonValue:
    """Convert a supported context value into a JSON-compatible value."""
    if value is None or isinstance(value, (str, bool, int)):
        return value

    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError(
                f"Floating-point log value must be finite: {value!r}."
            )
        return value

    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError(
                f"Decimal log value must be finite: {value!r}."
            )
        return format(value, "f")

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                "Datetime log values must include an explicit timezone."
            )
        return value.isoformat()

    if isinstance(value, date):
        return value.isoformat()

    if isinstance(value, Enum):
        return _normalize_json_value(value.value)

    if isinstance(value, Mapping):
        normalized_mapping: dict[str, JsonValue] = {}

        for key, nested_value in value.items():
            if not isinstance(key, str):
                raise TypeError(
                    "Nested log mapping keys must be strings."
                )

            normalized_mapping[key] = _normalize_json_value(
                nested_value
            )

        return normalized_mapping

    if isinstance(value, (list, tuple)):
        return [
            _normalize_json_value(item)
            for item in value
        ]

    if is_dataclass(value) and not isinstance(value, type):
        raise TypeError(
            "Dataclass instances must be converted to an explicit "
            "non-sensitive logging context before logging."
        )

    raise TypeError(
        "Unsupported logging context value type: "
        f"{type(value).__name__}."
    )


def _format_text_value(value: JsonValue) -> str:
    """Format one normalized context value without introducing new lines."""
    if isinstance(value, str):
        return json.dumps(
            value,
            ensure_ascii=False,
        )

    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )


def _format_timestamp(value: object) -> str:
    """Return an ISO 8601 timestamp from a Loguru record value."""
    if isinstance(value, datetime):
        return value.isoformat()

    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        formatted = isoformat()
        if isinstance(formatted, str):
            return formatted

    raise TypeError(
        "Loguru record timestamp does not support ISO 8601 formatting."
    )


def _format_level(value: object) -> str:
    """Return the textual level name from a Loguru record value."""
    name = getattr(value, "name", None)

    if not isinstance(name, str):
        raise TypeError(
            "Loguru record level does not contain a textual name."
        )

    return _normalize_level(
        name,
        field="record level",
    )


def _validate_sink(
    sink: Sink,
    *,
    field: str,
) -> None:
    """Validate a supported Loguru sink value."""
    if isinstance(sink, (str, Path)):
        if not str(sink):
            raise ValueError(f"{field} path must not be empty.")
        return

    if not callable(getattr(sink, "write", None)):
        raise TypeError(
            f"{field} must be a path or writable text stream, "
            f"received {type(sink).__name__}."
        )