"""`render_summary()` — the one shared completion-summary renderer (ticket
"Completion summary and exit codes", .scratch/interactive-cli map), used
identically by `cli/run.py` (non-interactive) and `interactive/provider.py`
(`show_summary` just delegates here). Pure output — no prompting — so it
uses `rich.Console` directly rather than the `InteractionProvider` Protocol.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from pyauditor.cli.bootstrap import BootstrapResult
from pyauditor.cli.consolidate import ConsolidateResult
from pyauditor.cli.measure import MeasureResult
from pyauditor.cli.report import ReportResult
from pyauditor.orchestration.run import RunResult, dependency_missing
from pyauditor.orchestration.state import CommandStateEntry

_STATE_ICON: dict[str, tuple[str, str]] = {
    "pending": ("○", "dim"),
    "running": ("◐", "cyan"),
    "done": ("●", "green"),
    "skipped": ("◌", "yellow"),
    "error": ("✕", "bold red"),
}


def exit_code_for_run(state_commands: tuple[CommandStateEntry, ...]) -> int:
    """`1` iff any Command ended `error`; `skipped` is a deliberate choice,
    never a failure (ticket "Failure-handling flow")."""
    return 1 if any(entry.status == "error" for entry in state_commands) else 0


_RESULT_TYPE_FOR_COMMAND: dict[str, type] = {
    "bootstrap": BootstrapResult,
    "measure": MeasureResult,
    "report": ReportResult,
    "consolidate": ConsolidateResult,
}


def _result_for(entry: CommandStateEntry, results: tuple[object, ...]) -> object | None:
    expected_type = _RESULT_TYPE_FOR_COMMAND[entry.command]
    for result in results:
        if not isinstance(result, expected_type):
            continue
        if entry.command == "consolidate" or getattr(result, "orgao", None) == entry.orgao:
            return result
    return None


def _bootstrap_artifact(result: BootstrapResult) -> str:
    return str(result.capa_path)


def _measure_artifact(result: MeasureResult) -> str:
    failing = [i.contractual_id for i in result.indicators if i.hard_failure]
    line = f"{len(result.indicators)} indicador(es) apurado(s)"
    if failing:
        line += f" — falhas: {', '.join(failing)}"
    return line


def _report_artifact(result: ReportResult) -> str:
    return f"{result.output_path} ({result.indicator_count} indicadores)"


def _consolidate_artifact(result: ConsolidateResult) -> str:
    return f"{result.output_path} ({result.decisions_preserved} decisão(ões) preservada(s))"


# Keyed the same way as `_RESULT_TYPE_FOR_COMMAND` — one type-discrimination
# point instead of two (a prior isinstance-chain here re-decided the same
# "which CommandResult subtype is this" question `_result_for` already answered).
_ARTIFACT_FORMATTER_FOR_TYPE: dict[type, Callable[[Any], str]] = {
    BootstrapResult: _bootstrap_artifact,
    MeasureResult: _measure_artifact,
    ReportResult: _report_artifact,
    ConsolidateResult: _consolidate_artifact,
}


def _artifact_line(entry: CommandStateEntry, result: object | None) -> str:
    if result is None:
        return "pulado" if entry.status == "skipped" else "—"
    formatter = _ARTIFACT_FORMATTER_FOR_TYPE.get(type(result))
    return formatter(result) if formatter is not None else "—"


def _next_steps(run_result: RunResult) -> list[str]:
    steps: list[str] = []
    for entry in run_result.state.commands:
        if entry.status == "done":
            continue
        missing = dependency_missing(entry.command, entry.orgao, run_result.request)
        if missing:
            steps.append(f"{entry.command} ({entry.orgao or '—'}): {', '.join(missing)}")
    return steps


def render_summary(
    run_result: RunResult, *, log_path: object | None = None, console: Console | None = None
) -> None:
    """Pure output — the exit code is a separate concern, `exit_code_for_run`."""
    console = console or Console()

    table = Table(box=None, show_header=True, header_style="bold")
    table.add_column("")
    table.add_column("Command")
    table.add_column("Órgão")
    table.add_column("Artefatos / avisos")

    for entry in run_result.state.commands:
        icon, style = _STATE_ICON[entry.status]
        result = _result_for(entry, run_result.results)
        detail = entry.error_message or _artifact_line(entry, result)
        table.add_row(f"[{style}]{icon}[/{style}]", entry.command, entry.orgao or "—", detail)

    console.print(table)

    if log_path is not None:
        console.print(f"[dim]Log completo: {log_path}[/dim]")

    steps = _next_steps(run_result)
    if steps:
        console.print(Panel("\n".join(steps), title="Próximos passos", border_style="cyan"))
