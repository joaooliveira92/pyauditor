"""Run-state persistence (ticket "Run orchestrator and resume",
.scratch/interactive-cli map): one JSON file per `(competencia,
orgao_selector)`, granularity per Command, reused/overwritten across
attempts, never auto-deleted. The filesystem (ticket "Dependency
enforcement") stays the source of truth for whether a Command *can* run —
this file only caches what the orchestrator already decided, for resume.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final, Literal

type CommandState = Literal["pending", "running", "done", "skipped", "error"]

_DEFAULT_RUNS_DIR: Final[Path] = Path(".pyauditor/runs")


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
    raw = json.loads(path.read_text(encoding="utf-8"))
    commands = tuple(CommandStateEntry(**entry) for entry in raw["commands"])
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
