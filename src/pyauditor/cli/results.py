"""Shared vocabulary for `run_*` results (ticket "Structured result
dataclasses", .scratch/interactive-cli map). `Status` only knows `done`/
`error` — that's a completed call's outcome, distinct from the fuller
Command state (pending/running/done/skipped/error) orchestration tracks.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final, Literal, Protocol

type Status = Literal["done", "error"]

_EXIT_CODES: Final[dict[Status, int]] = {"done": 0, "error": 1}


def exit_code_for(status: Status) -> int:
    return _EXIT_CODES[status]


class _HasStatus(Protocol):
    @property
    def status(self) -> Status: ...


def exit_code_for_results(results: Sequence[_HasStatus]) -> int:
    """Reduce a `--orgao both` fan-out (`list[MeasureResult]` etc.) to one
    exit code — `1` if any result errored, replacing the old `code |=
    run_measure(...)` bit-OR now that `run_*` no longer returns `int`.
    """
    return 1 if any(result.status == "error" for result in results) else 0


@dataclass(frozen=True, slots=True)
class DependencyCheck:
    """Result of a Command's precondition check (ticket "Dependency
    enforcement") — lives here, not in `cli/dependencies.py`, so each
    command file (which returns one) doesn't import from the registry
    that imports the command file's checker function.
    """

    satisfied: bool
    missing: tuple[str, ...]
