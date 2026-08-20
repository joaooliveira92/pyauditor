"""`pyauditor run <competencia>` — non-interactive, scriptable orchestration
of bootstrap→measure→report→consolidate in one invocation (ticket "Run
orchestrator and resume"). Thin wrapper: builds a `RunRequest` from the same
flags `measure`/`report`/`consolidate` already use, calls `execute_run` with
no-op callbacks, then renders the shared summary.

`run` always regenerates: it sets `force=True`, so the persisted run-state
never suppresses re-running a Command that a previous attempt already marked
done (unlike the interactive flow, which resumes where it left off).
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from pyauditor.orchestration.run import RunRequest, execute_run
from pyauditor.orchestration.summary import exit_code_for_run, render_summary

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
        force=True,
    )
    run_result = execute_run(request)
    render_summary(run_result)
    return exit_code_for_run(run_result.state.commands)
