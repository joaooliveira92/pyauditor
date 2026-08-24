"""Orchestrate resumable, phase-major audit runs.

This module owns the command sequencing shared by the non-interactive CLI and
the interactive flow. Both modes call :func:`execute_run`; interaction is
provided only through state-change and failure-decision callbacks.

Execution is phase-major:

1. bootstrap for every selected organization;
2. split for every selected organization;
3. measure for every selected organization;
4. report for every selected organization;
5. one organization-independent consolidation when both organizations are
   selected.

Persisted state supports command-level resume. The filesystem remains the
source of truth for dependency and artifact availability. A persisted
``done`` state is reused only while the command's expected artifact remains
available.

Every state transition is persisted before its callback is invoked. Dispatch
exceptions are converted into command failures, logged with their causal
exception, and passed through the same retry, skip, isolate, or abort policy
used by explicit error results.

The orchestrator intentionally does not provide file locking. Concurrent runs
targeting the same competence and organization selector are unsupported.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from pyauditor.categoria_filter import Warning
from pyauditor.logging import log_event, logger
from pyauditor.orchestration._decision import (
    FailureDecision,
    _abort_on_failure,
    handle_failure,
    isolate_on_failure,
)
from pyauditor.orchestration._flow_helpers import (
    find_entry,
    notify_state_change,
    now,
    sanitize_error_message,
    upsert,
)
from pyauditor.orchestration._warning_decision import (
    WarningDecision,
    continue_on_warning,
    validate_warning_decision,
)
from pyauditor.orchestration.command_dispatch import (
    dependency_missing,
    dispatch,
    own_artifact_missing,
)
from pyauditor.orchestration.plan import plan as build_plan
from pyauditor.orchestration.resume import ensure_state
from pyauditor.orchestration.state import (
    CommandStateEntry,
    RunState,
    save_state,
    state_path,
)
from pyauditor.periodo import PeriodoAfericao, month_bounds

__all__: Final[tuple[str, ...]] = (
    'FailureDecision',
    'RunRequest',
    'RunResult',
    'WarningDecision',
    'continue_on_warning',
    'dependency_missing',
    'execute_run',
    'isolate_on_failure',
)

type CommandResult = object
type PlanStep = tuple[str, str | None]
type ResultKey = tuple[str, str | None]

_ALL_COMMANDS: Final[frozenset[str]] = frozenset(
    {
        'bootstrap',
        'split',
        'measure',
        'report',
        'consolidate',
    }
)
_ORGANIZATION_COMMANDS: Final[frozenset[str]] = frozenset(
    {
        'bootstrap',
        'split',
        'measure',
        'report',
    }
)
_SUPPORTED_ORGAO_SELECTORS: Final[frozenset[str]] = frozenset(
    {
        'MinC',
        'MTur',
        'both',
    }
)
_DEFAULT_RUNS_DIR: Final[Path] = Path('.pyauditor/runs')


@dataclass(frozen=True, slots=True)
class RunRequest:
    """Describe one orchestration invocation.

    Attributes:
        competencia: Reporting period accepted by :func:`month_bounds`.
        orgao: Organization selector, either ``MinC``, ``MTur``, or ``both``.
        config_dir: Root of shared and organization-specific configurations.
        data_dir: Root of input data.
        output_dir: Root directory for generated ROMs.
        report_dir: Destination directory for report workbooks.
        capa_path: Base path used to resolve each organization's cover file.
        final_month: Whether report calculation uses final-month rules.
        commands: Commands enabled for this invocation.
        runs_dir: Directory containing persisted run-state documents.
        force: Whether previously completed or skipped commands must rerun.
        force_commands: Commands that must rerun even when persisted as
            completed or skipped.
        strict: Whether split and measure reject rows without period evidence.
    """

    competencia: str
    orgao: str
    config_dir: Path
    data_dir: Path
    output_dir: Path
    report_dir: Path
    capa_path: Path
    final_month: bool = False
    commands: frozenset[str] = _ALL_COMMANDS
    runs_dir: Path = _DEFAULT_RUNS_DIR
    force: bool = False
    force_commands: frozenset[str] = frozenset()
    strict: bool = False


@dataclass(frozen=True, slots=True)
class RunResult:
    """Represent the result of one orchestration invocation.

    ``started_at`` and ``finished_at`` describe only the current invocation.
    They do not include time spent by commands completed in previous resume
    attempts.

    Attributes:
        competencia: Reporting period processed by the run.
        orgao_selector: Organization selector used to build the plan.
        results: Latest result produced for each command and organization.
        state: Final persisted command state.
        request: Original validated request.
        started_at: Timezone-aware ISO 8601 invocation start timestamp.
        finished_at: Timezone-aware ISO 8601 invocation finish timestamp.
    """

    competencia: str
    orgao_selector: str
    results: tuple[CommandResult, ...]
    state: RunState
    request: RunRequest
    started_at: str
    finished_at: str


def _noop_state_change(_entry: CommandStateEntry) -> None:
    """Ignore a state transition."""
    return None


def _validate_request(request: RunRequest) -> PeriodoAfericao:
    """Validate an orchestration request before creating persistent state.

    Returns:
        The reporting-period bounds derived from the validated competence.

    Raises:
        TypeError: If ``request`` or its collection fields have invalid types.
        ValueError: If the organization selector or command sets are invalid,
            or if the competence cannot be parsed.
    """
    if not isinstance(request, RunRequest):
        raise TypeError(
            f'request deve ser RunRequest, recebido {type(request).__name__}'
        )

    if request.orgao not in _SUPPORTED_ORGAO_SELECTORS:
        raise ValueError(
            'orgao deve ser um de '
            f'{sorted(_SUPPORTED_ORGAO_SELECTORS)!r}, '
            f'recebido {request.orgao!r}'
        )

    if not isinstance(request.commands, frozenset):
        raise TypeError('commands deve ser um frozenset')

    if not isinstance(request.force_commands, frozenset):
        raise TypeError('force_commands deve ser um frozenset')

    unknown_commands = request.commands - _ALL_COMMANDS
    if unknown_commands:
        raise ValueError(
            f'commands contém valores não suportados:'
            f'{sorted(unknown_commands)!r}'
        )

    unknown_forced_commands = request.force_commands - _ALL_COMMANDS
    if unknown_forced_commands:
        raise ValueError(
            f'force_commands contém valores não suportados:'
            f'{sorted(unknown_forced_commands)!r}'
        )

    if not request.competencia.strip():
        raise ValueError('competencia não pode ser vazio')

    return month_bounds(request.competencia)


def _result_key(
    command: str,
    orgao: str | None,
) -> ResultKey:
    """Return the key used to retain the latest command result."""
    return (command, orgao)


def _ordered_results(
    plan: tuple[PlanStep, ...],
    results: dict[ResultKey, CommandResult],
) -> tuple[CommandResult, ...]:
    """Return latest command results in phase-major plan order."""
    return tuple(results[key] for key in plan if key in results)


def execute_run(
    request: RunRequest,
    on_state_change: Callable[
        [CommandStateEntry],
        None,
    ] = _noop_state_change,
    on_failure: Callable[
        [CommandStateEntry],
        FailureDecision,
    ] = _abort_on_failure,
    on_warning: Callable[
        [str, str | None, tuple[Warning, ...]],
        WarningDecision,
    ] = continue_on_warning,
) -> RunResult:
    """Execute or resume a phase-major orchestration run.

    State is persisted after every transition. Commands persisted as ``done``
    or ``skipped`` are reused unless the request forces execution or a required
    command-owned artifact is missing.

    Dispatch exceptions derived from ``Exception`` are converted into command
    failures. ``KeyboardInterrupt``, ``SystemExit``, and other
    ``BaseException`` subclasses propagate, leaving the persisted command in
    ``running`` state so the next invocation can reset it to ``pending``.

    Only the latest result for each command and organization is returned.
    Failed retry attempts therefore do not create ambiguous duplicate results.

    Args:
        request: Validated orchestration inputs and execution policy.
        on_state_change: Callback invoked after each persisted transition.
        on_failure: Callback that decides ``retry``, ``skip``, ``isolate``, or
            ``abort`` after a command failure.
        on_warning: Callback invoked after a command finishes ``done`` with
            non-empty ``result.warnings``. Decides ``continue`` (default —
            matches the direct, non-interactive flow), ``retry`` — dispatches
            the same command and organization again, letting the operator fix
            something outside the process (e.g. ``categorias.yaml``, an input
            CSV) before the run advances — or ``abort``. Unlike
            ``on_failure``, there is no ``skip``: the command already
            succeeded.

    Returns:
        The invocation result, including final state and latest command
        results.

    Raises:
        TypeError: If the request or callback results violate their contracts.
        ValueError: If the request, plan, or callback decision is invalid.
        OSError: If state persistence or command filesystem access fails.
        Exception: Propagates failures raised by run command callbacks.
    """
    session_started_at = now()
    periodo = _validate_request(request)
    plan = build_plan(request.orgao)
    state = ensure_state(
        request.competencia,
        request.orgao,
        request.runs_dir,
        plan,
    )
    path = state_path(
        request.competencia,
        request.orgao,
        request.runs_dir,
    )

    latest_results: dict[ResultKey, CommandResult] = {}
    skipped_steps: set[PlanStep] = set()
    # Etapas efetivamente executadas nesta invocação (não apenas reutilizadas
    # de uma passada anterior) — ticket 11: `already_split` de `measure` só
    # suprime os avisos de `in_values`/`outros` quando `split` rodou de fato
    # na mesma passada; numa retomada em que o `split` foi reutilizado
    # (done/skipped) e só o `measure` re-executou, os avisos continuam saindo
    # — `execute_run` decide e repassa ao `_dispatch`.
    executed_steps: set[PlanStep] = set()

    def finish_result() -> RunResult:
        return RunResult(
            competencia=request.competencia,
            orgao_selector=request.orgao,
            results=_ordered_results(
                plan,
                latest_results,
            ),
            state=state,
            request=request,
            started_at=session_started_at,
            finished_at=now(),
        )

    for command, orgao in plan:
        step = (command, orgao)

        if command not in request.commands:
            disabled_entry = CommandStateEntry(
                command=command,
                orgao=orgao,
                status='skipped',
                finished_at=now(),
                error_message=('comando desabilitado para esta execução'),
            )
            state = upsert(state, disabled_entry)
            save_state(path, state)
            notify_state_change(
                on_state_change,
                disabled_entry,
            )
            skipped_steps.add(step)
            continue

        if step in skipped_steps:
            continue

        current = find_entry(
            state,
            command,
            orgao,
        )
        stale_done = (
            current is not None
            and current.status == 'done'
            and own_artifact_missing(
                command,
                orgao,
                request,
            )
            is not None
        )

        if (
            current is not None
            and current.status in {'done', 'skipped'}
            and not request.force
            and command not in request.force_commands
            and not stale_done
        ):
            continue

        while True:
            missing = dependency_missing(
                command,
                orgao,
                request,
            )

            if missing:
                failed_at = now()
                state, decision = handle_failure(
                    state,
                    command=command,
                    orgao=orgao,
                    error_message='dependência não satisfeita: '
                    + '; '.join(missing),
                    started_at=failed_at,
                    finished_at=failed_at,
                    plan=plan,
                    path=path,
                    on_state_change=on_state_change,
                    on_failure=on_failure,
                    skipped_steps=skipped_steps,
                )

                if decision == 'retry':
                    continue

                if decision in {'skip', 'isolate'}:
                    break

                return finish_result()

            running_entry = CommandStateEntry(
                command=command,
                orgao=orgao,
                status='running',
                started_at=now(),
            )
            state = upsert(state, running_entry)
            save_state(path, state)
            notify_state_change(
                on_state_change,
                running_entry,
            )
            log_event(
                'run_step_started',
                f'▶ {command} · {orgao or "-"}',
                'INFO',
                command=command,
                orgao=orgao,
            )

            try:
                result = dispatch(
                    command,
                    orgao,
                    request,
                    periodo,
                    already_split=(
                        ('split', orgao) in executed_steps
                        if command == 'measure'
                        else False
                    ),
                )
            except Exception as exc:
                logger.exception(
                    'Command %s failed for orgao %s',
                    command,
                    orgao,
                )
                state, decision = handle_failure(
                    state,
                    command=command,
                    orgao=orgao,
                    error_message=sanitize_error_message(
                        str(exc),
                        fallback=(f'{type(exc).__name__} durante {command}'),
                    ),
                    started_at=(running_entry.started_at or now()),
                    finished_at=now(),
                    plan=plan,
                    path=path,
                    on_state_change=on_state_change,
                    on_failure=on_failure,
                    skipped_steps=skipped_steps,
                )

                if decision == 'retry':
                    continue

                if decision in {'skip', 'isolate'}:
                    break

                return finish_result()

            if getattr(result, 'status', None) == 'done':
                executed_steps.add(step)

            latest_results[_result_key(command, orgao)] = result

            if getattr(result, 'status', None) == 'done':
                done_entry = CommandStateEntry(
                    command=command,
                    orgao=orgao,
                    status='done',
                    started_at=(running_entry.started_at or now()),
                    finished_at=now(),
                )
                state = upsert(state, done_entry)
                save_state(path, state)
                notify_state_change(
                    on_state_change,
                    done_entry,
                )

                result_warnings = getattr(result, 'warnings', ())
                if result_warnings:
                    warning_decision = validate_warning_decision(
                        on_warning(
                            command,
                            orgao,
                            tuple(result_warnings),
                        )
                    )
                    if warning_decision == 'abort':
                        return finish_result()

                    if warning_decision == 'retry':
                        continue

                break

            state, decision = handle_failure(
                state,
                command=command,
                orgao=orgao,
                error_message=getattr(result, 'error_message', None),
                started_at=(running_entry.started_at or now()),
                finished_at=now(),
                plan=plan,
                path=path,
                on_state_change=on_state_change,
                on_failure=on_failure,
                skipped_steps=skipped_steps,
            )

            if decision == 'retry':
                continue

            if decision in {'skip', 'isolate'}:
                break

            return finish_result()

    return finish_result()
