"""`InteractionProvider` — the single injectable prompt/output protocol
(ticket "Interactive layer architecture", .scratch/interactive-cli map).
One flat Protocol, not several composed interfaces — every implementation
(real or test double) needs all of these together, so splitting wouldn't
buy any real seam. `RichQuestionaryProvider` is the production
implementation, wrapping `rich`+`questionary`.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import AbstractContextManager, contextmanager
from typing import Protocol

import questionary
from rich.console import Console

from pyauditor.orchestration.run import RunResult
from pyauditor.orchestration.summary import exit_code_for_run, render_summary


class InteractionProvider(Protocol):
    def ask_text(self, message: str, *, default: str = "", validate: object = None) -> str: ...

    def ask_choice(
        self, message: str, choices: Sequence[str], *, default: str | None = None
    ) -> str: ...

    def ask_multi_choice(
        self, message: str, choices: Sequence[tuple[str, str, bool, str | None]]
    ) -> list[str]:
        """`choices` is `(label, value, checked, disabled_reason)` — the
        visual form of `DependencyCheck` (ticket "Dependency enforcement"):
        a non-`None` `disabled_reason` makes the option unselectable."""
        ...

    def confirm(self, message: str, *, default: bool = True) -> bool: ...

    def show_message(self, text: str, *, style: str = "") -> None: ...

    def show_progress(self, label: str) -> AbstractContextManager[None]: ...

    def show_summary(self, run_result: RunResult, *, log_path: object | None = None) -> int: ...


class RichQuestionaryProvider:
    """Production `InteractionProvider` — a real TTY via `questionary`, output
    via `rich.Console`."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def ask_text(self, message: str, *, default: str = "", validate: object = None) -> str:
        answer = questionary.text(message, default=default, validate=validate).ask()
        return "" if answer is None else str(answer)

    def ask_choice(
        self, message: str, choices: Sequence[str], *, default: str | None = None
    ) -> str:
        answer = questionary.select(message, choices=list(choices), default=default).ask()
        return "" if answer is None else str(answer)

    def ask_multi_choice(
        self, message: str, choices: Sequence[tuple[str, str, bool, str | None]]
    ) -> list[str]:
        options = [
            questionary.Choice(label, value=value, checked=checked, disabled=disabled_reason)
            for label, value, checked, disabled_reason in choices
        ]
        answer = questionary.checkbox(message, choices=options).ask()
        return list(answer) if answer else []

    def confirm(self, message: str, *, default: bool = True) -> bool:
        answer = questionary.confirm(message, default=default).ask()
        return bool(answer)

    def show_message(self, text: str, *, style: str = "") -> None:
        self.console.print(f"[{style}]{text}[/{style}]" if style else text)

    @contextmanager
    def show_progress(self, label: str) -> Iterator[None]:
        with self.console.status(label, spinner="dots"):
            yield

    def show_summary(self, run_result: RunResult, *, log_path: object | None = None) -> int:
        render_summary(run_result, log_path=log_path, console=self.console)
        return exit_code_for_run(run_result.state.commands)
