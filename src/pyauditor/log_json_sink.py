"""Adapter de sink loguru→JSON achatado (plano, uma linha por registro).

Extraído de `logging.py` (ticket 06 SRP): isola a mecânica de escrever um
registro do Loguru como um objeto JSON flat no stream. A serialização de
valores e a validação de schema vivem em `log_contract` — este módulo só
orquestra um registro.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime
from threading import Lock
from typing import Final, TextIO, cast

from pyauditor.log_contract import (
    JsonValue,
    normalize_json_value,
    normalize_level,
    validate_event,
    validate_single_line_text,
)

__all__: Final[tuple[str, ...]] = ("FlatJsonSink",)

_IGNORED_EXTRA_KEYS: Final[frozenset[str]] = frozenset({"event_message", "detail"})


class FlatJsonSink:
    """Escrever registros do Loguru como objetos JSON planos estáveis."""

    def __init__(self, stream: TextIO) -> None:
        """Inicializa o sink com um stream de texto gravável."""
        if not callable(getattr(stream, "write", None)):
            raise TypeError("JSON log sink must provide a writable text interface.")

        self._stream = stream
        self._lock = Lock()

    def write(self, message: object) -> None:
        """Serializar e escrever uma mensagem do Loguru."""
        record = getattr(message, "record", None)
        if not isinstance(record, Mapping):
            raise TypeError("Loguru JSON sink received a message without a record.")

        record_values = cast(Mapping[str, object], record)

        extra_raw = record_values.get("extra", {})
        if not isinstance(extra_raw, Mapping):
            raise TypeError("Loguru record extra context must be a mapping.")

        extra_values = cast(Mapping[str, object], extra_raw)

        extra = {
            str(key): normalize_json_value(value)
            for key, value in extra_values.items()
            if key not in _IGNORED_EXTRA_KEYS
        }

        timestamp = record_values.get("time")
        level = record_values.get("level")

        event = extra_values.get("event", "unstructured_log")
        event_message = extra_values.get(
            "event_message",
            record_values.get("message", ""),
        )

        payload: dict[str, JsonValue] = {
            "time": format_timestamp(timestamp),
            "level": format_level(level),
            "event": validate_event(str(event)),
            "message": validate_single_line_text(
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


def format_timestamp(value: object) -> str:
    """Devolver um timestamp ISO 8601 de um valor de registro do Loguru."""
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


def format_level(value: object) -> str:
    """Devolver o nome textual do nível de um registro do Loguru."""
    name = getattr(value, "name", None)

    if not isinstance(name, str):
        raise TypeError("Loguru record level does not contain a textual name.")

    return normalize_level(name, field="record level")