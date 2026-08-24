"""Codec do estado persistido do `run` (ticket 02 SRP).

Decodificação, validação de invariantes e serialização do documento JSON de
estado de `orchestration/state.py`. O schema do documento — versão, campos
raiz, campos de comando, estados válidos e os helpers de restrição — vive
aqui; `state.py` cuida da persistência atômica e do naming de arquivo e
reexporta os tipos para preservar a API pública.

`load_state`/`save_state`/`reset_stale_running` (em `state.py`) chamam
`decode_state`, `validate_state` e `encode_state` como funções puras, sem
duplicação da regra do documento.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Final, Literal, cast

__all__: Final[tuple[str, ...]] = (
    'CommandState',
    'CommandStateEntry',
    'JsonObject',
    'RunState',
    'RunStateCorruptedError',
    'decode_state',
    'encode_state',
    'parse_iso_timestamp',
    'validate_state',
)

type CommandState = Literal[
    'pending',
    'running',
    'done',
    'skipped',
    'error',
]

type JsonObject = dict[str, object]

_COMMAND_FIELDS: Final[frozenset[str]] = frozenset(
    {
        'command',
        'orgao',
        'status',
        'started_at',
        'finished_at',
        'error_message',
    }
)

_SCHEMA_VERSION: Final[int] = 1

_STATE_COMPONENT_RE: Final[re.Pattern[str]] = re.compile(
    r'^[A-Za-z0-9][A-Za-z0-9._-]*$'
)

_ROOT_FIELDS: Final[frozenset[str]] = frozenset(
    {
        'schema_version',
        'competencia',
        'orgao_selector',
        'commands',
    }
)

_VALID_STATES: Final[frozenset[str]] = frozenset(
    {
        'pending',
        'running',
        'done',
        'skipped',
        'error',
    }
)


class RunStateCorruptedError(ValueError):
    """Report a run-state document that violates the persisted schema.

    Corruption includes invalid JSON, truncated content, unsupported schema
    versions, malformed fields, duplicate command entries, and invalid state
    transitions.

    Filesystem errors such as missing permissions or a path referring to a
    directory are not considered document corruption and propagate unchanged.

    Attributes:
        path: Path of the invalid state document.
        reason: Actionable description of the schema violation.
    """

    def __init__(self, path: Path, reason: str) -> None:
        """Initialize a corruption error for ``path``."""
        self.path = path
        self.reason = reason
        super().__init__(
            f'Run-state file {path} is corrupted ({reason}); delete it to '
            f'start the run again.'
        )


@dataclass(frozen=True, slots=True)
class CommandStateEntry:
    """Represent the persisted lifecycle state of one command.

    Timestamps use ISO 8601 strings with an explicit UTC offset. Naive
    timestamps are rejected.

    State invariants are:

    - ``pending`` has no timestamps or error message;
    - ``running`` has ``started_at`` but no terminal fields;
    - ``done`` has start and finish timestamps and no error message;
    - ``skipped`` has no start timestamp, requires ``finished_at``, and may
      carry a non-sensitive reason in ``error_message``;
    - ``error`` has start and finish timestamps and requires a non-empty,
      non-sensitive error message.

    Error messages must not contain credentials, tokens, complete payloads,
    or personally identifiable information.

    Attributes:
        command: Canonical command identifier.
        orgao: Organization associated with the command, when applicable.
        status: Current command lifecycle state.
        started_at: ISO 8601 execution start timestamp.
        finished_at: ISO 8601 terminal timestamp.
        error_message: Sanitized failure or skip explanation.
    """

    command: str
    orgao: str | None
    status: CommandState
    started_at: str | None = None
    finished_at: str | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class RunState:
    """Represent one resumable orchestration attempt.

    Attributes:
        competencia: Canonical reporting-period identifier.
        orgao_selector: Canonical organization selector.
        commands: Ordered command states for the orchestration plan.
    """

    competencia: str
    orgao_selector: str
    commands: tuple[CommandStateEntry, ...]


def decode_state(raw: object) -> RunState:
    """Decode a JSON-compatible object into a validated state model."""
    root = _require_object(raw, context='document root')
    _require_exact_fields(
        root,
        expected=_ROOT_FIELDS,
        context='document root',
    )

    schema_version = _require_integer(
        root,
        field='schema_version',
        context='document root',
    )
    if schema_version != _SCHEMA_VERSION:
        raise ValueError(
            f'unsupported schema_version {schema_version!r}; expected'
            f'{_SCHEMA_VERSION}'
        )

    competencia = _require_string(
        root,
        field='competencia',
        context='document root',
    )
    orgao_selector = _require_string(
        root,
        field='orgao_selector',
        context='document root',
    )

    raw_commands = root['commands']
    if not isinstance(raw_commands, list):
        raise TypeError("document root field 'commands' must be a list")

    commands = tuple(
        _decode_command(entry, index=index)
        for index, entry in enumerate(raw_commands)
    )

    return RunState(
        competencia=competencia,
        orgao_selector=orgao_selector,
        commands=commands,
    )


def validate_state(state: RunState) -> None:
    """Validate state and command-level domain invariants."""
    if not isinstance(state, RunState):
        raise TypeError(
            f'state must be RunState, received {type(state).__name__}'
        )

    _validate_path_component('competencia', state.competencia)
    _validate_path_component('orgao_selector', state.orgao_selector)

    if not isinstance(state.commands, tuple):
        raise TypeError('commands must be a tuple')

    seen_commands: set[tuple[str, str | None]] = set()

    for index, entry in enumerate(state.commands):
        if not isinstance(entry, CommandStateEntry):
            raise TypeError(
                f'commands[{index}] must be CommandStateEntry, received'
                f'{type(entry).__name__}'
            )

        _validate_command_entry(entry, index=index)

        key = (entry.command, entry.orgao)
        if key in seen_commands:
            raise ValueError(
                f'duplicate command state for command={entry.command!r},'
                f'orgao={entry.orgao!r}'
            )
        seen_commands.add(key)


def encode_state(state: RunState) -> str:
    """Serialize a run state into the persisted JSON document.

    The payload carries the schema version plus the command entries as
    ``dict``s. ``save_state`` (``state.py``) wraps this content in an atomic
    write; the encoding itself is pure.
    """
    payload = {
        'schema_version': _SCHEMA_VERSION,
        'competencia': state.competencia,
        'orgao_selector': state.orgao_selector,
        'commands': [asdict(entry) for entry in state.commands],
    }
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
    )
    return f'{serialized}\n'


def parse_iso_timestamp(
    value: str,
    *,
    field: str,
) -> datetime:
    """Parse a timezone-aware ISO 8601 timestamp (canonical helper).

    Fonte única da normalização do sufixo ``Z`` e da validação de offset
    explícito — reusada por `_parse_optional_timestamp` (state) e pelo resumo
    JSON (`summary_json`), que antes duplicavam a lógica (ticket 06 SRP).
    """
    normalized = f'{value[:-1]}+00:00' if value.endswith('Z') else value

    try:
        timestamp = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f'{field} must be a valid ISO 8601 timestamp') from exc

    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError(f'{field} must include an explicit UTC offset')

    return timestamp


def _decode_command(raw: object, *, index: int) -> CommandStateEntry:
    """Decode one command entry from a JSON-compatible object."""
    context = f'commands[{index}]'
    entry = _require_object(raw, context=context)
    _require_exact_fields(
        entry,
        expected=_COMMAND_FIELDS,
        context=context,
    )

    status_raw = _require_string(
        entry,
        field='status',
        context=context,
    )
    if status_raw not in _VALID_STATES:
        raise ValueError(f'{context} has unknown command status {status_raw!r}')

    return CommandStateEntry(
        command=_require_string(
            entry,
            field='command',
            context=context,
        ),
        orgao=_require_optional_string(
            entry,
            field='orgao',
            context=context,
        ),
        status=cast(CommandState, status_raw),
        started_at=_require_optional_string(
            entry,
            field='started_at',
            context=context,
        ),
        finished_at=_require_optional_string(
            entry,
            field='finished_at',
            context=context,
        ),
        error_message=_require_optional_string(
            entry,
            field='error_message',
            context=context,
        ),
    )


def _validate_command_entry(
    entry: CommandStateEntry,
    *,
    index: int,
) -> None:
    """Validate one command entry and its lifecycle fields."""
    context = f'commands[{index}]'

    _validate_non_empty_string(
        entry.command,
        field=f'{context}.command',
    )

    if entry.orgao is not None:
        _validate_non_empty_string(
            entry.orgao,
            field=f'{context}.orgao',
        )

    if entry.status not in _VALID_STATES:
        raise ValueError(f'{context}.status has unknown value {entry.status!r}')

    started_at = _parse_optional_timestamp(
        entry.started_at,
        field=f'{context}.started_at',
    )
    finished_at = _parse_optional_timestamp(
        entry.finished_at,
        field=f'{context}.finished_at',
    )

    if (
        started_at is not None
        and finished_at is not None
        and finished_at < started_at
    ):
        raise ValueError(f'{context}.finished_at must not precede started_at')

    if entry.error_message is not None:
        _validate_non_empty_string(
            entry.error_message,
            field=f'{context}.error_message',
        )

    if entry.status == 'pending':
        _require_absent(
            context,
            entry,
            'started_at',
            'finished_at',
            'error_message',
        )
        return

    if entry.status == 'running':
        _require_present(context, entry, 'started_at')
        _require_absent(
            context,
            entry,
            'finished_at',
            'error_message',
        )
        return

    if entry.status == 'done':
        _require_present(
            context,
            entry,
            'started_at',
            'finished_at',
        )
        _require_absent(context, entry, 'error_message')
        return

    if entry.status == 'skipped':
        _require_absent(context, entry, 'started_at')
        _require_present(context, entry, 'finished_at')
        return

    if entry.status == 'error':
        _require_present(
            context,
            entry,
            'started_at',
            'finished_at',
            'error_message',
        )


def _validate_path_component(field: str, value: str) -> None:
    """Validate a canonical identifier used in a state filename."""
    _validate_non_empty_string(value, field=field)

    if _STATE_COMPONENT_RE.fullmatch(value) is None:
        raise ValueError(
            f"{field} must contain only ASCII letters, digits, '.', '_', and"
            f"'-': {value!r}"
        )

    if value in {'.', '..'}:
        raise ValueError(f'{field} must not be a path traversal component')


def _validate_non_empty_string(value: object, *, field: str) -> None:
    """Require a non-empty string without surrounding whitespace."""
    if not isinstance(value, str):
        raise TypeError(
            f'{field} must be a string, received {type(value).__name__}'
        )

    if not value:
        raise ValueError(f'{field} must not be empty')

    if value != value.strip():
        raise ValueError(f'{field} must not contain surrounding whitespace')


def _parse_optional_timestamp(
    value: str | None,
    *,
    field: str,
) -> datetime | None:
    """Parse an optional timezone-aware ISO 8601 timestamp."""
    if value is None:
        return None

    _validate_non_empty_string(value, field=field)
    return parse_iso_timestamp(value, field=field)


def _require_present(
    context: str,
    entry: CommandStateEntry,
    *fields: str,
) -> None:
    """Require command fields to contain non-None values."""
    for field in fields:
        if getattr(entry, field) is None:
            raise ValueError(
                f'{context}.{field} is required for status {entry.status!r}'
            )


def _require_absent(
    context: str,
    entry: CommandStateEntry,
    *fields: str,
) -> None:
    """Require command fields to contain None."""
    for field in fields:
        if getattr(entry, field) is not None:
            raise ValueError(
                f'{context}.{field} must be absent for status {entry.status!r}'
            )


def _require_object(raw: object, *, context: str) -> JsonObject:
    """Require a JSON object with string keys."""
    if not isinstance(raw, dict):
        raise TypeError(
            f'{context} must be an object, received {type(raw).__name__}'
        )

    if any(not isinstance(key, str) for key in raw):
        raise TypeError(f'{context} must contain only string keys')

    return cast(JsonObject, raw)


def _require_exact_fields(
    raw: JsonObject,
    *,
    expected: frozenset[str],
    context: str,
) -> None:
    """Require exactly the supported fields in a JSON object."""
    actual = frozenset(raw)

    missing = sorted(expected - actual)
    extra = sorted(actual - expected)

    if missing:
        raise ValueError(f'{context} is missing required fields: {missing!r}')

    if extra:
        raise ValueError(f'{context} contains unsupported fields: {extra!r}')


def _require_string(
    raw: JsonObject,
    *,
    field: str,
    context: str,
) -> str:
    """Return a required string from a JSON object."""
    value = raw[field]
    if not isinstance(value, str):
        raise TypeError(f'{context} field {field!r} must be a string')
    return value


def _require_optional_string(
    raw: JsonObject,
    *,
    field: str,
    context: str,
) -> str | None:
    """Return an optional string from a JSON object."""
    value = raw[field]
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f'{context} field {field!r} must be a string or null')
    return value


def _require_integer(
    raw: JsonObject,
    *,
    field: str,
    context: str,
) -> int:
    """Return a required non-boolean integer from a JSON object."""
    value = raw[field]
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f'{context} field {field!r} must be an integer')
    return value
