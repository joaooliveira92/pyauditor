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

from pathlib import Path
from typing import Final

from pyauditor.orchestration.run import RunRequest, execute_run, isolate_on_failure
from pyauditor.orchestration.summary import OutputFormat, exit_code_for_run, render_summary

_DEFAULT_RUNS_DIR: Final[Path] = Path(".pyauditor/runs")


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
    output: OutputFormat = "text",
    force: bool = False,
    strict: bool = False,
) -> int:
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
        force_commands=frozenset({"report", "consolidate"}),
        strict=strict,
    )
    run_result = execute_run(request, on_failure=isolate_on_failure)
    render_summary(run_result, output=output)
    return exit_code_for_run(run_result.state.commands, run_result.results)
