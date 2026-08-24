"""`pyauditor run <competencia>` — non-interactive, scriptable orchestration
of bootstrap→measure→report→consolidate in one invocation (ticket "Run
orchestrator and resume"). Thin wrapper: builds a `RunRequest` from the same
flags `measure`/`report`/`consolidate` already use, calls `execute_run` with
an `isolate`-on-failure policy, then renders the shared summary.

Ticket "08 - Transacionalidade do pipeline por órgão": `run` is transactional
per órgão, not for the whole invocation — a failure in one órgão never
aborts the other's still-pending steps (`on_failure=isolate_on_failure`, which
cascades only within the failed órgão + the shared `consolidate`). `run`
resumes by default: `force=False`, so a persisted `done` Command from a
previous attempt is not re-run — matching the interactive flow — except
`report`/`consolidate`, always re-dispatched (`force_commands`) since they're
cheap to regenerate from already-materialized ROMs and the completion summary
(ticket 04) needs a fresh `Result` to report accurate publicable/glosa status
even for an órgão whose upstream steps were skipped this invocation. Pass
`--force` to force a full reprocessing (e.g. after manually fixing
`capa.csv`/`objetos.csv`).
"""

from __future__ import annotations

from contextlib import suppress
from pathlib import Path
from typing import Final, Literal

from rich.console import Console
from rich.prompt import Prompt

from pyauditor.orchestration._warning_decision import (
    WarningDecision,
    continue_on_warning,
)
from pyauditor.orchestration.run import (
    RunRequest,
    execute_run,
    isolate_on_failure,
)
from pyauditor.orchestration.summary import (
    OutputFormat,
    exit_code_for_run,
    render_summary,
)

_DEFAULT_RUNS_DIR: Final[Path] = Path('.pyauditor/runs')

type OnWarningMode = Literal['continue', 'pause']

_VALID_ON_WARNING_MODES: Final[frozenset[str]] = frozenset(
    {'continue', 'pause'}
)


_ON_WARNING_PROMPT_CHOICES: Final[dict[str, WarningDecision]] = {
    'c': 'continue',
    'r': 'retry',
    'a': 'abort',
}


def _pause_on_warning(
    command: str,
    orgao: str | None,
    warnings: tuple[str, ...],
) -> WarningDecision:
    """Ask the operator how to proceed after a step finished with warnings.

    Prompts on stderr, alongside the log stream, so it never interleaves with
    the stdout summary. ``retry`` gives the operator a real third option
    besides "run anyway" and "give up entirely": fix something outside the
    process — ``categorias.yaml``, an input CSV — then have the same command
    and organization dispatched again before the run advances.
    """
    console = Console(stderr=True)
    console.print(
        f'[yellow]{len(warnings)} aviso(s) em {command} '
        f'({orgao or "-"}):[/yellow]'
    )
    for warning in warnings:
        console.print(f'  • {warning}')

    try:
        choice = Prompt.ask(
            'continuar mesmo assim (c), corrigir e tentar de novo (r), '
            'ou abortar (a)?',
            choices=list(_ON_WARNING_PROMPT_CHOICES),
            default='c',
            console=console,
        )
    except (EOFError, KeyboardInterrupt):
        console.print(
            '[bold red]entrada interativa indisponível — abortando.[/bold red]'
        )
        return 'abort'

    decision = _ON_WARNING_PROMPT_CHOICES[choice]

    if decision == 'retry':
        console.print(
            '[cyan]Ajuste o que for necessário (categorias.yaml, CSV de '
            f'entrada etc.) e pressione Enter para refazer {command} '
            f'({orgao or "-"}).[/cyan]'
        )
        with suppress(EOFError, KeyboardInterrupt):
            Prompt.ask('Pronto', console=console, default='')

    return decision


def run_run(
    competencia: str,
    orgao: str,
    config_dir: Path,
    data_dir: Path,
    output_dir: Path,
    report_dir: Path,
    capa_path: Path,
    *,
    final_month: bool = False,
    runs_dir: Path = _DEFAULT_RUNS_DIR,
    output: OutputFormat = 'text',
    force: bool = False,
    strict: bool = False,
    on_warning: OnWarningMode = 'continue',
) -> int:
    if on_warning not in _VALID_ON_WARNING_MODES:
        raise ValueError(f'Unsupported on_warning mode: {on_warning!r}.')

    request = RunRequest(
        competencia=competencia,
        orgao=orgao,
        config_dir=config_dir,
        data_dir=data_dir,
        output_dir=output_dir,
        report_dir=report_dir,
        capa_path=capa_path,
        final_month=final_month,
        runs_dir=runs_dir,
        force=force,
        force_commands=frozenset({'report', 'consolidate'}),
        strict=strict,
    )
    run_result = execute_run(
        request,
        on_failure=isolate_on_failure,
        on_warning=(
            _pause_on_warning if on_warning == 'pause' else continue_on_warning
        ),
    )
    render_summary(run_result, output=output)
    return exit_code_for_run(run_result.state.commands, run_result.results)
