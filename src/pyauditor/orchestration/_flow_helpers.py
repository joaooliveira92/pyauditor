"""Helpers de fluxo do orquestrador (ticket 05 SRP).

Pequenas funções compartilhadas entre `orchestration/run.py` e
`orchestration/_decision.py`: timestamps, sanitização de mensagens de erro e
manipulação imutável de `RunState` (busca/substituição de entrada). Evita o
ciclo de import entre `run` e `_decision`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime

from pyauditor.orchestration.state import (
    CommandStateEntry,
    RunState,
)

__all__: tuple[str, ...] = (
    'find_entry',
    'notify_state_change',
    'sanitize_error_message',
    'upsert',
)

_MAX_ERROR_MESSAGE_LENGTH: int = 2_000


def now() -> str:
    """Return the current UTC time as a timezone-aware ISO 8601 string."""
    return datetime.now(UTC).isoformat()


def sanitize_error_message(
    message: str | None,
    *,
    fallback: str,
) -> str:
    """Return a bounded, single-line message suitable for persisted state."""
    value = message or fallback
    sanitized = ' '.join(value.split())

    if not sanitized:
        sanitized = fallback

    if len(sanitized) > _MAX_ERROR_MESSAGE_LENGTH:
        return sanitized[: _MAX_ERROR_MESSAGE_LENGTH - 3] + '...'

    return sanitized


def find_entry(
    state: RunState,
    command: str,
    orgao: str | None,
) -> CommandStateEntry | None:
    """Find one command state by command and organization."""
    for entry in state.commands:
        if entry.command == command and entry.orgao == orgao:
            return entry

    return None


def upsert(
    state: RunState,
    entry: CommandStateEntry,
) -> RunState:
    """Replace a command entry without changing plan order.

    A new entry is appended only when the state does not already contain its
    command and organization key.
    """
    key = (entry.command, entry.orgao)
    replaced = False
    commands: list[CommandStateEntry] = []

    for current in state.commands:
        if (current.command, current.orgao) == key:
            if replaced:
                raise ValueError(
                    'Run state contains duplicate command entries for '
                    f'command={entry.command!r}, orgao={entry.orgao!r}'
                )

            commands.append(entry)
            replaced = True
        else:
            commands.append(current)

    if not replaced:
        commands.append(entry)

    return replace(state, commands=tuple(commands))


def notify_state_change(
    callback: Callable[[CommandStateEntry], None],
    entry: CommandStateEntry,
) -> None:
    """Invoke a state callback after its transition is persisted.

    Callback failures propagate because the caller controls the interaction
    boundary. The persisted transition remains available for resume.
    """
    callback(entry)
