"""Test double for `InteractionProvider` (ticket "Interactive layer
architecture") — plays back a scripted list of answers and records every
`show_*` call for assertions. Test-only infrastructure, never imported by
`src/`.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field

from pyauditor.interactive.provider import InteractionCancelledError
from pyauditor.orchestration.run import RunResult

CANCEL = object()
"""Script this sentinel as an answer to simulate Ctrl+C/EOF at that prompt —
`_next()` raises `InteractionCancelledError` instead of returning it."""


@dataclass
class FakeInteractionProvider:
    answers: list[object] = field(default_factory=list)
    messages: list[tuple[str, str]] = field(default_factory=list)
    progress_labels: list[str] = field(default_factory=list)
    summaries: list[RunResult] = field(default_factory=list)
    _cursor: int = field(default=0, init=False)

    def _next(self) -> object:
        answer = self.answers[self._cursor]
        self._cursor += 1
        if answer is CANCEL:
            raise InteractionCancelledError
        return answer

    def ask_text(
        self, message: str, *, default: str = '', validate: object = None
    ) -> str:
        return str(self._next())

    def ask_choice(
        self,
        message: str,
        choices: Sequence[str],
        *,
        default: str | None = None,
    ) -> str:
        return str(self._next())

    def ask_multi_choice(
        self, message: str, choices: Sequence[tuple[str, str, bool, str | None]]
    ) -> list[str]:
        answer = self._next()
        return list(answer) if isinstance(answer, list) else []

    def confirm(self, message: str, *, default: bool = True) -> bool:
        return bool(self._next())

    def show_message(self, text: str, *, style: str = '') -> None:
        self.messages.append((text, style))

    @contextmanager
    def show_progress(self, label: str) -> Iterator[None]:
        self.progress_labels.append(label)
        yield

    def show_summary(
        self, run_result: RunResult, *, log_path: object | None = None
    ) -> int:
        self.summaries.append(run_result)
        return (
            1
            if any(e.status == 'error' for e in run_result.state.commands)
            else 0
        )
