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


class InteractionCancelled(Exception):
    """Raised by an `InteractionProvider` when the user cancels (Ctrl+C/EOF)
    at a prompt — never silently coerced into an empty/false answer. Caught
    once at the top of the guided flow (`flow.py::run_guided_flow`) to exit
    cleanly instead of corrupting an in-progress answer (ticket "Interactive
    layer architecture": "Ctrl+C encerra sem perder o preenchido")."""


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
        if answer is None:
            raise InteractionCancelled
        return str(answer)

    def ask_choice(
        self, message: str, choices: Sequence[str], *, default: str | None = None
    ) -> str:
        answer = questionary.select(message, choices=list(choices), default=default).ask()
        if answer is None:
            raise InteractionCancelled
        return str(answer)

    def ask_multi_choice(
        self, message: str, choices: Sequence[tuple[str, str, bool, str | None]]
    ) -> list[str]:
        options = [
            questionary.Choice(label, value=value, checked=checked, disabled=disabled_reason)
            for label, value, checked, disabled_reason in choices
        ]
        answer = questionary.checkbox(message, choices=options).ask()
        if answer is None:
            raise InteractionCancelled
        return list(answer)

    def confirm(self, message: str, *, default: bool = True) -> bool:
        answer = questionary.confirm(message, default=default).ask()
        if answer is None:
            raise InteractionCancelled
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
