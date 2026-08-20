"""Interactive layer entry point — `run_interactive()`, called by `cli_main`
when invoked with no arguments (non-TTY already ruled out by the caller)."""

from __future__ import annotations

from pyauditor.interactive.flow import run_guided_flow
from pyauditor.interactive.provider import RichQuestionaryProvider

__all__ = ("run_interactive",)


def run_interactive() -> int:
    return run_guided_flow(RichQuestionaryProvider())
