"""Persist orchestration state for resumable command execution.

Each run stores one JSON document for a unique ``competencia`` and
``orgao_selector`` pair. State is tracked at command granularity and retained
across attempts until explicitly removed.

The persisted state is a resume cache, not the source of truth for command
eligibility or output existence. Before executing a command, the orchestrator
must continue to validate its filesystem dependencies and outputs.

A command left in ``running`` state indicates that the previous process ended
before recording a terminal result. On the next invocation,
:func:`reset_stale_running` returns that command to ``pending`` so it can be
executed again from the beginning.

State documents are schema-versioned and written atomically. A failed write
must not replace the last complete checkpoint. This module intentionally does
not implement file locking. Concurrent processes targeting the same state file
are unsupported and may overwrite one another.

O codec do documento — tipos, decodificação, validação de invariantes e
serialização — vive em `orchestration/state_codec.py` (ticket 02 SRP); este
módulo cuida do naming de arquivo, da persistência atômica e da reexportação
da API pública, que fica inalterada.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Final

from pyauditor.atomic_write import atomic_write
from pyauditor.orchestration import state_codec as _codec
from pyauditor.orchestration.state_codec import (
    CommandState,
    CommandStateEntry,
    RunState,
    RunStateCorruptedError,
    parse_iso_timestamp,
)

__all__: Final[tuple[str, ...]] = (
    'CommandState',
    'CommandStateEntry',
    'RunState',
    'RunStateCorruptedError',
    'load_state',
    'parse_iso_timestamp',
    'reset_stale_running',
    'save_state',
    'state_path',
)

_DEFAULT_RUNS_DIR: Final[Path] = Path('.pyauditor/runs')


def state_path(
    competencia: str,
    orgao_selector: str,
    runs_dir: Path = _DEFAULT_RUNS_DIR,
) -> Path:
    """Return the state path for a reporting period and organization selector.

    Both identifiers must be non-empty filename-safe canonical values. Path
    separators, traversal components, whitespace, and shell punctuation are
    rejected rather than normalized.

    The filename uses a length-prefixed organization selector to avoid
    ambiguous concatenation when either identifier contains hyphens.

    Args:
        competencia: Canonical reporting-period identifier.
        orgao_selector: Canonical organization selector.
        runs_dir: Directory containing state documents.

    Returns:
        The path of the associated versioned JSON state document.

    Raises:
        ValueError: If either identifier is not filename-safe.
    """
    _codec._validate_path_component('competencia', competencia)
    _codec._validate_path_component('orgao_selector', orgao_selector)

    filename = f'{competencia}--{len(orgao_selector)}-{orgao_selector}.json'
    return runs_dir / filename


def load_state(path: Path) -> RunState | None:
    """Load and validate a persisted run state.

    Args:
        path: State document to read.

    Returns:
        The validated state, or ``None`` when the path does not exist.

    Raises:
        RunStateCorruptedError: If the file contains invalid JSON or
            violates the supported state schema.
        IsADirectoryError: If ``path`` refers to a directory.
        PermissionError: If the file cannot be read.
        OSError: If another filesystem error prevents reading.
        UnicodeDecodeError: If the file is not valid UTF-8.
    """
    if not path.exists():
        return None

    raw_text = path.read_text(encoding='utf-8')

    try:
        raw = json.loads(raw_text)
        state = _codec.decode_state(raw)
        _codec.validate_state(state)
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        if isinstance(exc, RunStateCorruptedError):
            raise
        raise RunStateCorruptedError(path, str(exc)) from exc

    return state


def save_state(path: Path, state: RunState) -> None:
    """Validate and atomically persist a run state.

    The destination directory is created when necessary. Serialization occurs
    before the atomic replacement, so an invalid state or serialization error
    cannot replace the previous checkpoint.

    Args:
        path: Destination JSON state path.
        state: State to validate and persist.

    Raises:
        ValueError: If ``state`` violates the domain invariants.
        OSError: If the destination directory or file cannot be written or
            atomically replaced.
    """
    _codec.validate_state(state)
    content = _codec.encode_state(state)

    path.parent.mkdir(parents=True, exist_ok=True)

    def write_state_file(temporary_path: Path) -> None:
        temporary_path.write_text(content, encoding='utf-8')

    atomic_write(path, write_state_file)


def reset_stale_running(state: RunState) -> RunState:
    """Reset interrupted commands so they can run again from the beginning.

    Entries not in ``running`` state are returned unchanged. A stale running
    entry becomes ``pending`` and has all attempt-specific timestamps and
    error information cleared.

    Args:
        state: Previously loaded and validated run state.

    Returns:
        A new state containing the reset stale commands.

    Raises:
        ValueError: If the supplied state is invalid.
    """
    _codec.validate_state(state)

    commands = tuple(
        replace(
            entry,
            status='pending',
            started_at=None,
            finished_at=None,
            error_message=None,
        )
        if entry.status == 'running'
        else entry
        for entry in state.commands
    )

    reset_state = replace(state, commands=commands)
    _codec.validate_state(reset_state)
    return reset_state
