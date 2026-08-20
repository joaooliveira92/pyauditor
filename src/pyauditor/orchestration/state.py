"""Run-state persistence (ticket "Run orchestrator and resume",
.scratch/interactive-cli map): one JSON file per `(competencia,
orgao_selector)`, granularity per Command, reused/overwritten across
attempts, never auto-deleted. The filesystem (ticket "Dependency
enforcement") stays the source of truth for whether a Command *can* run —
this file only caches what the orchestrator already decided, for resume.

No file locking — two processes targeting the same `(competencia,
orgao_selector)` concurrently is an accepted scope cut (design ticket "Run
orchestrator and resume": single-user CLI, not built preventively for a
concurrency profile this tool doesn't have).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final, Literal

type CommandState = Literal["pending", "running", "done", "skipped", "error"]

_VALID_STATES: Final[frozenset[str]] = frozenset({"pending", "running", "done", "skipped", "error"})

_DEFAULT_RUNS_DIR: Final[Path] = Path(".pyauditor/runs")


class RunStateCorrupted(Exception):
    """Raised by `load_state` when the run-state file at `path` is not the
    shape this module wrote — hand-edited, truncated by a crash mid-write,
    or from an incompatible version. Deleting the file starts the run over
    from scratch (the filesystem, not this file, is the source of truth for
    what actually ran — ticket "Dependency enforcement")."""

    def __init__(self, path: Path, reason: str) -> None:
        super().__init__(
            f"run-state file {path} is corrupted ({reason}) — delete it to start over"
        )


@dataclass(frozen=True, slots=True)
class CommandStateEntry:
    command: str
    orgao: str | None
    status: CommandState
    started_at: str | None = None
    finished_at: str | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class RunState:
    competencia: str
    orgao_selector: str
    commands: tuple[CommandStateEntry, ...]


def state_path(competencia: str, orgao_selector: str, runs_dir: Path = _DEFAULT_RUNS_DIR) -> Path:
    return runs_dir / f"{competencia}-{orgao_selector}.json"


def load_state(path: Path) -> RunState | None:
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        commands = tuple(CommandStateEntry(**entry) for entry in raw["commands"])
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise RunStateCorrupted(path, str(exc)) from exc
    for entry in commands:
        if entry.status not in _VALID_STATES:
            raise RunStateCorrupted(path, f"unknown Command state {entry.status!r}")
    return RunState(
        competencia=raw["competencia"], orgao_selector=raw["orgao_selector"], commands=commands
    )


def save_state(path: Path, state: RunState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "competencia": state.competencia,
        "orgao_selector": state.orgao_selector,
        "commands": [asdict(entry) for entry in state.commands],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def reset_stale_running(state: RunState) -> RunState:
    """A Command left `running` when the process died is stale on the next
    invocation — reset to `pending` so it's re-run from scratch (per-Command
    granularity, never resumed mid-Command)."""
    fixed = tuple(
        entry if entry.status != "running" else CommandStateEntry(
            command=entry.command, orgao=entry.orgao, status="pending",
        )
        for entry in state.commands
    )
    return RunState(
        competencia=state.competencia, orgao_selector=state.orgao_selector, commands=fixed
    )
