"""Contrato e serialização dos eventos de auditoria — **sem** `loguru` e sem
sinks. Responsabilidades (extraídas de `logging.py`, ticket 06 SRP):

- validar o identificador de evento/identificadores de contexto;
- normalizar valores de contexto para JSON (Decimal, Path, datetime, Enum,
  Mapping, listas) e formatar valores para texto legível;
- política anti-secret (chaves reservadas/sensíveis).

Vive separado da bridge do loguru para o schema do evento e a serialização
serem testáveis sem handlers globais e para o `_FlatJsonSink` depender só
daqui (sem risco de ciclo de import).
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from math import isfinite
from pathlib import Path
from typing import Final, cast

type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]

_DEFAULT_DETAIL_LEVEL: Final[int] = 0
_MAX_DETAIL_LEVEL: Final[int] = 2

_SUPPORTED_LEVELS: Final[frozenset[str]] = frozenset(
    {
        'DEBUG',
        'INFO',
        'WARNING',
        'ERROR',
        'CRITICAL',
    }
)

_EVENT_RE: Final[re.Pattern[str]] = re.compile(r'^[a-z][a-z0-9_]*$')
_CONTEXT_KEY_RE: Final[re.Pattern[str]] = re.compile(
    r'^[a-zA-Z_][a-zA-Z0-9_]*$'
)

_RESERVED_CONTEXT_KEYS: Final[frozenset[str]] = frozenset(
    {
        'time',
        'level',
        'event',
        'message',
        'detail',
    }
)

_SENSITIVE_KEY_FRAGMENTS: Final[frozenset[str]] = frozenset(
    {
        'api_key',
        'authorization',
        'credential',
        'password',
        'secret',
        'token',
    }
)


def normalize_level(level: str, *, field: str) -> str:
    """Validar e normalizar um nível de severidade suportado."""
    if type(level) is not str:
        raise TypeError(
            f'{field} must be a string, received {type(level).__name__}.'
        )

    normalized = level.strip().upper()

    if normalized not in _SUPPORTED_LEVELS:
        raise ValueError(
            f'Unsupported {field} {level!r}; expected one of'
            f'{sorted(_SUPPORTED_LEVELS)!r}.'
        )

    return normalized


def validate_detail(detail: int) -> int:
    """Validar um nível de detalhe de evento."""
    if type(detail) is not int:
        raise TypeError(
            f'detail must be an integer, received {type(detail).__name__}.'
        )

    if not 0 <= detail <= _MAX_DETAIL_LEVEL:
        raise ValueError(
            f'detail must be between 0 and {_MAX_DETAIL_LEVEL}, received'
            f'{detail}.'
        )

    return detail


def validate_event(event: str) -> str:
    """Validar um identificador de evento estável."""
    if type(event) is not str:
        raise TypeError(
            f'event must be a string, received {type(event).__name__}.'
        )

    normalized = event.strip()

    if _EVENT_RE.fullmatch(normalized) is None:
        raise ValueError(
            'event must use snake_case and match '
            f'{_EVENT_RE.pattern!r}, received {event!r}.'
        )

    return normalized


def validate_single_line_text(value: str, *, field: str) -> str:
    """Exigir texto não vazio e sem quebras de linha."""
    if type(value) is not str:
        raise TypeError(
            f'{field} must be a string, received {type(value).__name__}.'
        )

    normalized = value.strip()

    if not normalized:
        raise ValueError(f'{field} must not be empty.')

    if '\n' in normalized or '\r' in normalized:
        raise ValueError(f'{field} must contain exactly one line.')

    return normalized


def normalize_context(context: Mapping[str, object]) -> dict[str, JsonValue]:
    """Validar chaves de contexto e normalizar valores para sinks JSON/texto."""
    normalized: dict[str, JsonValue] = {}

    for key, value in context.items():
        if type(key) is not str:
            raise TypeError(
                f'Context keys must be strings, received {type(key).__name__}.'
            )

        normalized_key = key.strip()

        if _CONTEXT_KEY_RE.fullmatch(normalized_key) is None:
            raise ValueError(f'Invalid context key: {key!r}.')

        if normalized_key in _RESERVED_CONTEXT_KEYS:
            raise ValueError(f'Context key {normalized_key!r} is reserved.')

        lowered_key = normalized_key.lower()
        if any(
            fragment in lowered_key for fragment in _SENSITIVE_KEY_FRAGMENTS
        ):
            raise ValueError(
                f'Context key {normalized_key!r} may contain sensitive data.'
            )

        if value is None:
            continue

        normalized[normalized_key] = normalize_json_value(value)

    return normalized


def normalize_json_value(value: object) -> JsonValue:
    """Converter um valor de contexto suportado para valor JSON-compatível."""
    if value is None or isinstance(value, (str, bool, int)):
        return value

    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError(
                f'Floating-point log value must be finite: {value!r}.'
            )
        return value

    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError(f'Decimal log value must be finite: {value!r}.')
        return format(value, 'f')

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                'Datetime log values must include an explicit timezone.'
            )
        return value.isoformat()

    if isinstance(value, date):
        return value.isoformat()

    if isinstance(value, Enum):
        return normalize_json_value(value.value)

    if isinstance(value, Mapping):
        normalized_mapping: dict[str, JsonValue] = {}
        value_typed = cast(Mapping[str, object], value)

        for key, nested_value in value_typed.items():
            if type(key) is not str:
                raise TypeError('Nested log mapping keys must be strings.')

            normalized_mapping[key] = normalize_json_value(nested_value)

        return normalized_mapping

    if isinstance(value, (list, tuple)):
        return [
            normalize_json_value(item) for item in cast(Sequence[object], value)
        ]

    if is_dataclass(value) and not isinstance(value, type):
        raise TypeError(
            'Dataclass instances must be converted to an explicit '
            'non-sensitive logging context before logging.'
        )

    raise TypeError(
        f'Unsupported logging context value type: {type(value).__name__}.'
    )


def format_text_value(value: JsonValue) -> str:
    """Formatar um valor de contexto normalizado sem introduzir novas linhas."""
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)

    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(',', ':'),
        allow_nan=False,
    )
