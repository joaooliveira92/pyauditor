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
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, Literal, cast

from pyauditor.capa_paths import resolve_capa_path
from pyauditor.cli.bootstrap import BootstrapResult, run_bootstrap
from pyauditor.cli.consolidate import (
    ConsolidateResult,
    check_consolidate_ready,
    run_consolidate,
)
from pyauditor.cli.dependencies import CHECKERS
from pyauditor.cli.measure import MeasureResult, run_measure
from pyauditor.cli.report import (
    ReportResult,
    check_report_ready,
    run_report,
)
from pyauditor.cli.split import (
    _SINTETICO_FILENAME,
    SplitResult,
    run_split,
)
from pyauditor.config.resolution import per_orgao_paths
from pyauditor.excel.equipe import EQUIPE_FILENAME
from pyauditor.excel.objetos import OBJETOS_FILENAME
from pyauditor.excel.prazos import PRAZOS_FILENAME
from pyauditor.logging import logger
from pyauditor.orchestration.state import (
    CommandStateEntry,
    RunState,
    RunStateCorrupted,
    load_state,
    reset_stale_running,
    save_state,
    state_path,
)
from pyauditor.periodo import PeriodoAfericao, month_bounds

__all__: Final[tuple[str, ...]] = (
    "FailureDecision",
    "RunRequest",
    "RunResult",
    "dependency_missing",
    "execute_run",
    "isolate_on_failure",
)

type CommandResult = (
    BootstrapResult | SplitResult | MeasureResult | ReportResult | ConsolidateResult
)
type FailureDecision = Literal[
    "retry",
    "skip",
    "isolate",
    "abort",
]
type PlanStep = tuple[str, str | None]
type ResultKey = tuple[str, str | None]

_ALL_COMMANDS: Final[frozenset[str]] = frozenset(
    {
        "bootstrap",
        "split",
        "measure",
        "report",
        "consolidate",
    }
)
_ORGANIZATION_COMMANDS: Final[frozenset[str]] = frozenset(
    {
        "bootstrap",
        "split",
        "measure",
        "report",
    }
)
_SUPPORTED_ORGAO_SELECTORS: Final[frozenset[str]] = frozenset(
    {
        "MinC",
        "MTur",
        "both",
    }
)
_FAILURE_DECISIONS: Final[frozenset[str]] = frozenset(
    {
        "retry",
        "skip",
        "isolate",
        "abort",
    }
)
_PHASE_ORDER: Final[tuple[str, ...]] = (
    "bootstrap",
    "split",
    "measure",
    "report",
    "consolidate",
)
_PHASE_INDEX: Final[dict[str, int]] = {command: index for index, command in enumerate(_PHASE_ORDER)}

_MAX_ERROR_MESSAGE_LENGTH: Final[int] = 2_000
_DEFAULT_RUNS_DIR: Final[Path] = Path(".pyauditor/runs")


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


def _abort_on_failure(_entry: CommandStateEntry) -> FailureDecision:
    """Abort after the first command failure."""
    return "abort"


def isolate_on_failure(
    _entry: CommandStateEntry,
) -> FailureDecision:
    """Isolate a failed organization while preserving technical failure.

    The failed command remains in ``error`` state so the aggregate exit code
    reports a technical failure. Later commands for the same organization and
    the shared consolidation are marked ``skipped``. Commands belonging to
    another organization remain eligible to run.
    """
    return "isolate"


def _now() -> str:
    """Return the current UTC time as a timezone-aware ISO 8601 string."""
    return datetime.now(UTC).isoformat()


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
        raise TypeError(f"request must be RunRequest, received {type(request).__name__}")

    if request.orgao not in _SUPPORTED_ORGAO_SELECTORS:
        raise ValueError(
            "orgao must be one of "
            f"{sorted(_SUPPORTED_ORGAO_SELECTORS)!r}, "
            f"received {request.orgao!r}"
        )

    if not isinstance(request.commands, frozenset):
        raise TypeError("commands must be a frozenset")

    if not isinstance(request.force_commands, frozenset):
        raise TypeError("force_commands must be a frozenset")

    unknown_commands = request.commands - _ALL_COMMANDS
    if unknown_commands:
        raise ValueError(f"commands contains unsupported values: {sorted(unknown_commands)!r}")

    unknown_forced_commands = request.force_commands - _ALL_COMMANDS
    if unknown_forced_commands:
        raise ValueError(
            f"force_commands contains unsupported values: {sorted(unknown_forced_commands)!r}"
        )

    if not request.competencia.strip():
        raise ValueError("competencia must not be empty")

    return month_bounds(request.competencia)


def _plan(orgao_selector: str) -> tuple[PlanStep, ...]:
    """Build the phase-major execution plan."""
    if orgao_selector not in _SUPPORTED_ORGAO_SELECTORS:
        raise ValueError(f"Unsupported organization selector: {orgao_selector!r}")

    organizations = ("MinC", "MTur") if orgao_selector == "both" else (orgao_selector,)

    steps: list[PlanStep] = []

    for command in (
        "bootstrap",
        "split",
        "measure",
        "report",
    ):
        for organization in organizations:
            steps.append((command, organization))

    if orgao_selector == "both":
        steps.append(("consolidate", None))

    return tuple(steps)


def _find_entry(
    state: RunState,
    command: str,
    orgao: str | None,
) -> CommandStateEntry | None:
    """Find one command state by command and organization."""
    for entry in state.commands:
        if entry.command == command and entry.orgao == orgao:
            return entry

    return None


def _upsert(
    state: RunState,
    entry: CommandStateEntry,
) -> RunState:
    """Replace a command entry without changing plan order.

    A new entry is appended only when the state does not already contain its
    command and organization key.
    """
    key = (entry.command, entry.orgao)
    replaced = False
    commands: list[CommandStateEntry] = []

    for current in state.commands:
        if (current.command, current.orgao) == key:
            if replaced:
                raise ValueError(
                    "Run state contains duplicate command entries for "
                    f"command={entry.command!r}, orgao={entry.orgao!r}"
                )

            commands.append(entry)
            replaced = True
        else:
            commands.append(current)

    if not replaced:
        commands.append(entry)

    return replace(state, commands=tuple(commands))


def _reconcile_state(
    existing: RunState,
    request: RunRequest,
    plan: tuple[PlanStep, ...],
) -> RunState:
    """Reconcile persisted command state with the current execution plan.

    Obsolete entries are removed. Existing entries belonging to the current
    plan are preserved and reordered according to the current phase-major
    plan. Missing entries are initialized as ``pending``.
    """
    if existing.competencia != request.competencia:
        raise RunStateCorrupted(
            state_path(
                request.competencia,
                request.orgao,
                request.runs_dir,
            ),
            "persisted competencia does not match the current request",
        )

    if existing.orgao_selector != request.orgao:
        raise RunStateCorrupted(
            state_path(
                request.competencia,
                request.orgao,
                request.runs_dir,
            ),
            "persisted orgao_selector does not match the current request",
        )

    reset_state = reset_stale_running(existing)
    entries = {(entry.command, entry.orgao): entry for entry in reset_state.commands}

    commands = tuple(
        entries.get(
            (command, orgao),
            CommandStateEntry(
                command=command,
                orgao=orgao,
                status="pending",
            ),
        )
        for command, orgao in plan
    )

    return RunState(
        competencia=request.competencia,
        orgao_selector=request.orgao,
        commands=commands,
    )


def _ensure_state(
    request: RunRequest,
    plan: tuple[PlanStep, ...],
) -> RunState:
    """Load, recover, and reconcile persisted orchestration state."""
    path = state_path(
        request.competencia,
        request.orgao,
        request.runs_dir,
    )

    try:
        existing = load_state(path)
    except RunStateCorrupted as exc:
        logger.warning(
            "%s; starting the run from filesystem state",
            exc,
        )
        existing = None

    if existing is None:
        return RunState(
            competencia=request.competencia,
            orgao_selector=request.orgao,
            commands=tuple(
                CommandStateEntry(
                    command=command,
                    orgao=orgao,
                    status="pending",
                )
                for command, orgao in plan
            ),
        )

    try:
        return _reconcile_state(
            existing,
            request,
            plan,
        )
    except RunStateCorrupted as exc:
        logger.warning(
            "%s; starting the run from filesystem state",
            exc,
        )
        return RunState(
            competencia=request.competencia,
            orgao_selector=request.orgao,
            commands=tuple(
                CommandStateEntry(
                    command=command,
                    orgao=orgao,
                    status="pending",
                )
                for command, orgao in plan
            ),
        )


def _require_orgao(
    command: str,
    orgao: str | None,
) -> str:
    """Return the organization required by an organization-specific command."""
    if command not in _ORGANIZATION_COMMANDS:
        raise ValueError(f"Command {command!r} is not organization-specific")

    if orgao not in {"MinC", "MTur"}:
        raise ValueError(f"Command {command!r} requires orgao 'MinC' or 'MTur', received {orgao!r}")

    return orgao


def dependency_missing(
    command: str,
    orgao: str | None,
    request: RunRequest,
) -> tuple[str, ...]:
    """Return missing upstream dependencies for one planned command.

    Report and consolidation checks are dispatched explicitly so their typed
    parameter contracts remain visible to static analysis. Zero-argument
    checkers use the runtime registry.

    Raises:
        ValueError: If the command is unknown or its organization contract is
            invalid.
    """
    if command == "report":
        organization = _require_orgao(command, orgao)
        check = check_report_ready(
            request.competencia,
            organization,
            request.capa_path,
            request.output_dir / organization,
            data_dir=request.data_dir,
        )
        return check.missing

    if command == "consolidate":
        if orgao is not None:
            raise ValueError("consolidate must not receive an organization")

        check = check_consolidate_ready(
            request.competencia,
            request.report_dir,
            request.output_dir,
        )
        return check.missing

    if command not in _ORGANIZATION_COMMANDS:
        raise ValueError(f"Unsupported command: {command!r}")

    _require_orgao(command, orgao)

    checker = CHECKERS.get(command)
    if checker is None:
        raise ValueError(f"No dependency checker registered for command {command!r}")

    return checker().missing


def _own_artifact_missing(
    command: str,
    orgao: str | None,
    request: RunRequest,
) -> str | None:
    """Return an actionable message when a completed artifact disappeared.

    This check applies to commands whose dependency checkers do not validate
    their own outputs. Report and consolidation are normally regenerated by
    ``force_commands`` and are therefore excluded.
    """
    if command == "bootstrap":
        organization = _require_orgao(command, orgao)
        capa_path = resolve_capa_path(
            request.capa_path,
            organization,
        )

        if not capa_path.is_file():
            return f"capa de {organization} ausente em {capa_path}; execute bootstrap novamente"

        return None

    if command == "split":
        organization = _require_orgao(command, orgao)
        sintetico_path = (
            request.report_dir / organization / request.competencia / _SINTETICO_FILENAME
        )

        if not sintetico_path.is_file():
            return f"artefato de split ausente em {sintetico_path}; execute split novamente"

        return None

    if command == "measure":
        organization = _require_orgao(command, orgao)
        roms_dir = request.output_dir / organization / request.competencia

        if not roms_dir.is_dir():
            return f"diretório de ROMs ausente em {roms_dir}; execute measure novamente"

        return None

    if command in {"report", "consolidate"}:
        return None

    raise ValueError(f"Unsupported command: {command!r}")


def _dispatch(
    command: str,
    orgao: str | None,
    request: RunRequest,
    periodo: PeriodoAfericao,
    *,
    already_split: bool = False,
) -> CommandResult:
    """Execute one planned command using validated arguments.

    ``already_split`` (ticket 05/11): only honored by `measure` — whether
    `split` actually ran in this invocation, so the in-memory categorical
    path can suppress the duplicate `in_values`/`outros` warnings it would
    otherwise re-emit for the same raw dataset.
    """
    if command == "bootstrap":
        organization = _require_orgao(command, orgao)
        capa_path = resolve_capa_path(
            request.capa_path,
            organization,
        )
        return run_bootstrap(capa_path, organization)

    if command == "split":
        organization = _require_orgao(command, orgao)
        paths = per_orgao_paths(
            config_dir=request.config_dir,
            data_dir=request.data_dir,
            output_dir=request.output_dir,
            report_dir=request.report_dir,
            orgao=organization,
        )

        return run_split(
            request.competencia,
            paths.config_dir,
            paths.data_dir,
            expected_orgao=organization,
            manifest=paths.manifest,
            report_dir=paths.report_dir,
            materialize=False,
            periodo=periodo,
            strict=request.strict,
            prazos_path=request.data_dir / PRAZOS_FILENAME,
            capa_path=request.capa_path,
            equipe_path=request.data_dir / EQUIPE_FILENAME,
            objetos_path=request.data_dir / OBJETOS_FILENAME,
        )

    if command == "measure":
        organization = _require_orgao(command, orgao)
        paths = per_orgao_paths(
            config_dir=request.config_dir,
            data_dir=request.data_dir,
            output_dir=request.output_dir,
            orgao=organization,
        )

        return run_measure(
            competencia=request.competencia,
            config_dir=paths.config_dir,
            data_dir=paths.data_dir,
            output_dir=paths.output_dir,
            manifest=paths.manifest,
            expected_orgao=organization,
            equipe_path=request.data_dir / EQUIPE_FILENAME,
            periodo=periodo,
            strict=request.strict,
            # `run` always dispatches split immediately before measure for the
            # same organization/competência (ticket 05) — split already
            # logged the empty-window WARN/discard INFO and the in_values/
            # outros avisos for the same raw dataset, so measure's in-memory
            # categorical path skips them. Só quando `split` rodou de fato
            # nesta invocação (não numa retomada em que foi reutilizado).
            already_split=already_split,
        )

    if command == "report":
        organization = _require_orgao(command, orgao)
        paths = per_orgao_paths(
            config_dir=request.config_dir,
            data_dir=request.data_dir,
            output_dir=request.output_dir,
            orgao=organization,
        )
        output_path = request.report_dir / f"relatorio_{request.competencia}_{organization}.xlsx"

        return run_report(
            competencia=request.competencia,
            capa_path=request.capa_path,
            roms_dir=paths.output_dir,
            output_path=output_path,
            config_dir=paths.config_dir,
            expected_orgao=organization,
            is_final_month=request.final_month,
            data_dir=request.data_dir,
        )

    if command == "consolidate":
        if orgao is not None:
            raise ValueError("consolidate must not receive an organization")

        output_path = request.report_dir / f"relatorio_{request.competencia}_consolidado.xlsx"

        return run_consolidate(
            competencia=request.competencia,
            report_dir=request.report_dir,
            roms_dir=request.output_dir,
            output_path=output_path,
            data_dir=request.data_dir,
            is_final_month=request.final_month,
        )

    raise ValueError(f"Unsupported command: {command!r}")


def _downstream(
    plan: tuple[PlanStep, ...],
    command: str,
    orgao: str | None,
) -> tuple[PlanStep, ...]:
    """Return all planned steps that transitively depend on one command."""
    start_index = _PHASE_INDEX.get(command)
    if start_index is None:
        raise ValueError(f"Unsupported command: {command!r}")

    downstream: list[PlanStep] = []

    for later_command, later_orgao in plan:
        later_index = _PHASE_INDEX.get(later_command)
        if later_index is None:
            raise ValueError(f"Unsupported planned command: {later_command!r}")

        if later_command == "consolidate" and command != "consolidate":
            downstream.append((later_command, later_orgao))
            continue

        if later_orgao == orgao and later_index > start_index:
            downstream.append((later_command, later_orgao))

    return tuple(downstream)


def _sanitize_error_message(
    message: str | None,
    *,
    fallback: str,
) -> str:
    """Return a bounded, single-line message suitable for persisted state."""
    value = message or fallback
    sanitized = " ".join(value.split())

    if not sanitized:
        sanitized = fallback

    if len(sanitized) > _MAX_ERROR_MESSAGE_LENGTH:
        return sanitized[: _MAX_ERROR_MESSAGE_LENGTH - 3] + "..."

    return sanitized


def _validate_failure_decision(
    decision: object,
) -> FailureDecision:
    """Validate a decision returned by the failure callback."""
    if not isinstance(decision, str):
        raise TypeError(
            f"on_failure must return a string decision, received {type(decision).__name__}"
        )

    if decision not in _FAILURE_DECISIONS:
        raise ValueError(f"on_failure returned an unsupported decision: {decision!r}")

    return cast(FailureDecision, decision)


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


def _notify_state_change(
    callback: Callable[[CommandStateEntry], None],
    entry: CommandStateEntry,
) -> None:
    """Invoke a state callback after its transition is persisted.

    Callback failures propagate because the caller controls the interaction
    boundary. The persisted transition remains available for resume.
    """
    callback(entry)


def _cascade_skip(
    plan: tuple[PlanStep, ...],
    command: str,
    orgao: str | None,
    state: RunState,
    path: Path,
    on_state_change: Callable[[CommandStateEntry], None],
    skipped_steps: set[PlanStep],
    *,
    reason: str,
) -> RunState:
    """Mark every dependent planned step as skipped."""
    for later_command, later_orgao in _downstream(
        plan,
        command,
        orgao,
    ):
        step = (later_command, later_orgao)
        if step in skipped_steps:
            continue

        current = _find_entry(
            state,
            later_command,
            later_orgao,
        )
        if current is not None and current.status == "done":
            continue

        entry = CommandStateEntry(
            command=later_command,
            orgao=later_orgao,
            status="skipped",
            finished_at=_now(),
            error_message=_sanitize_error_message(
                reason,
                fallback="etapa ignorada por falha anterior",
            ),
        )
        skipped_steps.add(step)
        state = _upsert(state, entry)
        save_state(path, state)
        _notify_state_change(on_state_change, entry)

    return state


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
        on_failure: Callback that chooses ``retry``, ``skip``, ``isolate``, or
            ``abort`` after a command failure.

    Returns:
        The invocation result, including final state and latest command
        results.

    Raises:
        TypeError: If the request or callback results violate their contracts.
        ValueError: If the request, plan, or callback decision is invalid.
        OSError: If state persistence or command filesystem access fails.
        Exception: Propagates failures raised by state-change callbacks.
    """
    session_started_at = _now()
    periodo = _validate_request(request)
    plan = _plan(request.orgao)
    state = _ensure_state(request, plan)
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
    # (done/skipped) e só o `measure` re-executou, os avisos continuam saindo.
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
            finished_at=_now(),
        )

    def record_failure_and_decide(
        command: str,
        orgao: str | None,
        error_message: str | None,
        *,
        started_at: str,
        finished_at: str,
    ) -> FailureDecision:
        nonlocal state

        safe_message = _sanitize_error_message(
            error_message,
            fallback="comando terminou com erro sem mensagem",
        )
        error_entry = CommandStateEntry(
            command=command,
            orgao=orgao,
            status="error",
            started_at=started_at,
            finished_at=finished_at,
            error_message=safe_message,
        )
        state = _upsert(state, error_entry)
        save_state(path, state)
        _notify_state_change(
            on_state_change,
            error_entry,
        )

        decision = _validate_failure_decision(on_failure(error_entry))

        if decision == "skip":
            skipped_entry = CommandStateEntry(
                command=command,
                orgao=orgao,
                status="skipped",
                finished_at=_now(),
                error_message=safe_message,
            )
            state = _upsert(state, skipped_entry)
            save_state(path, state)
            _notify_state_change(
                on_state_change,
                skipped_entry,
            )

        if decision in {"skip", "isolate"}:
            state = _cascade_skip(
                plan,
                command,
                orgao,
                state,
                path,
                on_state_change,
                skipped_steps,
                reason=(f"etapa dependente de {command} ({orgao or 'global'}) não executada"),
            )

        return decision

    for command, orgao in plan:
        step = (command, orgao)

        if command not in request.commands:
            disabled_entry = CommandStateEntry(
                command=command,
                orgao=orgao,
                status="skipped",
                finished_at=_now(),
                error_message=("comando desabilitado para esta execução"),
            )
            state = _upsert(state, disabled_entry)
            save_state(path, state)
            _notify_state_change(
                on_state_change,
                disabled_entry,
            )
            skipped_steps.add(step)
            continue

        if step in skipped_steps:
            continue

        current = _find_entry(
            state,
            command,
            orgao,
        )
        stale_done = (
            current is not None
            and current.status == "done"
            and _own_artifact_missing(
                command,
                orgao,
                request,
            )
            is not None
        )

        if (
            current is not None
            and current.status in {"done", "skipped"}
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
                failed_at = _now()
                decision = record_failure_and_decide(
                    command,
                    orgao,
                    "dependência não satisfeita: " + "; ".join(missing),
                    started_at=failed_at,
                    finished_at=failed_at,
                )

                if decision == "retry":
                    continue

                if decision in {"skip", "isolate"}:
                    break

                return finish_result()

            running_entry = CommandStateEntry(
                command=command,
                orgao=orgao,
                status="running",
                started_at=_now(),
            )
            state = _upsert(state, running_entry)
            save_state(path, state)
            _notify_state_change(
                on_state_change,
                running_entry,
            )

            try:
                result = _dispatch(
                    command,
                    orgao,
                    request,
                    periodo,
                    already_split=(
                        ("split", orgao) in executed_steps if command == "measure" else False
                    ),
                )
            except Exception as exc:
                logger.exception(
                    "Command %s failed for orgao %s",
                    command,
                    orgao,
                )
                decision = record_failure_and_decide(
                    command,
                    orgao,
                    _sanitize_error_message(
                        str(exc),
                        fallback=(f"{type(exc).__name__} durante {command}"),
                    ),
                    started_at=(running_entry.started_at or _now()),
                    finished_at=_now(),
                )

                if decision == "retry":
                    continue

                if decision in {"skip", "isolate"}:
                    break

                return finish_result()

            if result.status == "done":
                executed_steps.add(step)

            latest_results[_result_key(command, orgao)] = result

            if result.status == "done":
                done_entry = CommandStateEntry(
                    command=command,
                    orgao=orgao,
                    status="done",
                    started_at=(running_entry.started_at or _now()),
                    finished_at=_now(),
                )
                state = _upsert(state, done_entry)
                save_state(path, state)
                _notify_state_change(
                    on_state_change,
                    done_entry,
                )
                break

            decision = record_failure_and_decide(
                command,
                orgao,
                result.error_message,
                started_at=(running_entry.started_at or _now()),
                finished_at=_now(),
            )

            if decision == "retry":
                continue

            if decision in {"skip", "isolate"}:
                break

            return finish_result()

    return finish_result()
