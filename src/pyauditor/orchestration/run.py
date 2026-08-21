"""Run orchestrator (ticket "Run orchestrator and resume", homed here per
ticket "Interactive layer architecture" — sequencing that `pyauditor run`
and the interactive layer need identically). Phase-major: bootstrap for
every órgão, then split, then measure for every órgão, then report for
every órgão, then one órgão-agnostic consolidate.

`cli/run.py` calls `execute_run` with no-op callbacks; `interactive/flow.py`
calls the same function, wiring its `InteractionProvider` as
`on_state_change`/`on_failure`. Zero business logic duplicated between the
two modes.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, Literal

from pyauditor.cli.bootstrap import BootstrapResult, run_bootstrap
from pyauditor.cli.consolidate import ConsolidateResult, check_consolidate_ready, run_consolidate
from pyauditor.cli.dependencies import CHECKERS
from pyauditor.cli.measure import MeasureResult, run_measure
from pyauditor.cli.report import ReportResult, check_report_ready, run_report
from pyauditor.cli.split import SplitResult, run_split
from pyauditor.config.manifest import DatasetManifest, load_manifest
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

type CommandResult = (
    BootstrapResult | SplitResult | MeasureResult | ReportResult | ConsolidateResult
)
type FailureDecision = Literal["retry", "skip", "isolate", "abort"]

_DEFAULT_CAPA_NAME: Final[str] = "capa.csv"
_ALL_COMMANDS: Final[frozenset[str]] = frozenset(
    {"bootstrap", "split", "measure", "report", "consolidate"}
)
_PHASE_ORDER: Final[tuple[str, ...]] = ("bootstrap", "split", "measure", "report", "consolidate")


@dataclass(frozen=True, slots=True)
class RunRequest:
    competencia: str
    orgao: str  # "MinC" | "MTur" | "both"
    config_dir: Path
    data_dir: Path
    output_dir: Path  # roms base dir
    report_dir: Path
    capa_path: Path
    final_month: bool = False
    commands: frozenset[str] = _ALL_COMMANDS
    runs_dir: Path = Path(".pyauditor/runs")
    force: bool = False  # re-run commands the persisted state already marked done/skipped
    # ticket 08: resume still always re-dispatches these commands regardless of
    # persisted done/skipped status — `run` (cli/run.py) sets {"report",
    # "consolidate"}: cheap to regenerate from already-materialized ROMs, and
    # the completion summary (ticket 04) needs a fresh Result to report
    # accurate publicable/glosa status even for an órgão skipped this invocation
    force_commands: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class RunResult:
    competencia: str
    orgao_selector: str
    results: tuple[CommandResult, ...]
    state: RunState
    request: RunRequest
    started_at: str
    finished_at: str


def _noop_state_change(_entry: CommandStateEntry) -> None:
    return None


def _abort_on_failure(_entry: CommandStateEntry) -> FailureDecision:
    return "abort"


def isolate_on_failure(_entry: CommandStateEntry) -> FailureDecision:
    """Ticket "08 - Transacionalidade do pipeline por órgão": a política de
    `on_failure` do `run` não-interativo. Diferente de `"skip"` (decisão de
    um humano, que reclassifica o próprio comando falho para `skipped`),
    `"isolate"` preserva `status="error"` no comando que de fato falhou —
    para que `exit_code_for_run` continue enxergando a falha técnica (código
    `1`, contrato do ticket 03) — e cascateia via `_cascade_skip`/`_downstream`
    só as etapas posteriores do mesmo órgão + o `consolidate` compartilhado.
    Uma falha no MTur nunca impede o loop de `execute_run` de seguir para as
    etapas do MinC ainda pendentes."""
    return "isolate"


def _capa_path_for(capa_path: Path, orgao: str) -> Path:
    """Delegates to ``pyauditor.capa_paths.resolve_capa_path`` — single
    implementation shared with ``cli/main.py`` (issue 05)."""
    from pyauditor.capa_paths import resolve_capa_path

    return resolve_capa_path(capa_path, orgao)


def _plan(orgao_selector: str) -> tuple[tuple[str, str | None], ...]:
    orgaos = ("MinC", "MTur") if orgao_selector == "both" else (orgao_selector,)
    steps: list[tuple[str, str | None]] = []
    for command in ("bootstrap", "split", "measure", "report"):
        for orgao in orgaos:
            steps.append((command, orgao))
    if orgao_selector == "both":
        steps.append(("consolidate", None))
    return tuple(steps)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _find_entry(state: RunState, command: str, orgao: str | None) -> CommandStateEntry | None:
    for entry in state.commands:
        if entry.command == command and entry.orgao == orgao:
            return entry
    return None


def _upsert(state: RunState, entry: CommandStateEntry) -> RunState:
    remaining = tuple(
        e for e in state.commands if not (e.command == entry.command and e.orgao == entry.orgao)
    )
    return RunState(
        competencia=state.competencia,
        orgao_selector=state.orgao_selector,
        commands=(*remaining, entry),
    )


def _ensure_state(request: RunRequest, plan: tuple[tuple[str, str | None], ...]) -> RunState:
    path = state_path(request.competencia, request.orgao, request.runs_dir)
    try:
        existing = load_state(path)
    except RunStateCorrupted as exc:
        logger.warning(f"{exc} — starting this run from scratch")
        existing = None
    if existing is None:
        commands = tuple(CommandStateEntry(command=c, orgao=o, status="pending") for c, o in plan)
        return RunState(
            competencia=request.competencia, orgao_selector=request.orgao, commands=commands
        )
    fixed = reset_stale_running(existing)
    for command, orgao in plan:
        if _find_entry(fixed, command, orgao) is None:
            entry = CommandStateEntry(command=command, orgao=orgao, status="pending")
            fixed = _upsert(fixed, entry)
    return fixed


def dependency_missing(command: str, orgao: str | None, request: RunRequest) -> tuple[str, ...]:
    """`report`/`consolidate` are called through their real, fully-typed
    function so mypy can catch a wrong-arity/wrong-type call — `CHECKERS`'s
    `Callable[..., DependencyCheck]` erases each checker's actual parameter
    list, so routing every call through it would let a mismatched call
    silently pass type-checking. `bootstrap`/`measure` take no arguments, so
    the erasure is harmless for them — they're the registry's genuine use
    case: a runtime string→checker lookup for the zero-arg case, where
    `command` is a loop variable, not statically known."""
    if command == "report":
        capa_path = request.capa_path
        roms_dir = request.output_dir / (orgao or "")
        check = check_report_ready(
            request.competencia, orgao or "", capa_path, roms_dir, data_dir=request.data_dir
        )
    elif command == "consolidate":
        check = check_consolidate_ready(request.competencia, request.report_dir, request.output_dir)
    else:
        check = CHECKERS[command]()
    return check.missing


def _manifest_for(per_orgao_config_dir: Path) -> DatasetManifest | None:
    manifest_path = per_orgao_config_dir / "datasets.yaml"
    return load_manifest(manifest_path) if manifest_path.exists() else None


def _dispatch(command: str, orgao: str | None, request: RunRequest) -> CommandResult:
    if command == "bootstrap":
        capa_path = _capa_path_for(request.capa_path, orgao or "")
        return run_bootstrap(capa_path, orgao or "")
    if command == "split":
        per_orgao_config_dir = request.config_dir / (orgao or "")
        return run_split(
            request.competencia,
            per_orgao_config_dir,
            request.data_dir / (orgao or ""),
            expected_orgao=orgao or "",
            manifest=_manifest_for(per_orgao_config_dir),
            output_dir=request.output_dir / (orgao or ""),
        )
    if command == "measure":
        per_orgao_config_dir = request.config_dir / (orgao or "")
        return run_measure(
            competencia=request.competencia,
            config_dir=per_orgao_config_dir,
            data_dir=request.data_dir / (orgao or ""),
            output_dir=request.output_dir / (orgao or ""),
            manifest=_manifest_for(per_orgao_config_dir),
            expected_orgao=orgao,
            capa_path=_capa_path_for(request.capa_path, orgao or ""),
        )
    if command == "report":
        output_path = request.report_dir / f"relatorio_{request.competencia}_{orgao}.xlsx"
        return run_report(
            competencia=request.competencia,
            capa_path=request.capa_path,
            roms_dir=request.output_dir / (orgao or ""),
            output_path=output_path,
            config_dir=request.config_dir / (orgao or ""),
            expected_orgao=orgao,
            is_final_month=request.final_month,
            data_dir=request.data_dir,
        )
    output_path = request.report_dir / f"relatorio_{request.competencia}_consolidado.xlsx"
    return run_consolidate(
        competencia=request.competencia,
        report_dir=request.report_dir,
        roms_dir=request.output_dir,
        output_path=output_path,
        data_dir=request.data_dir,
    )


def _downstream(
    plan: tuple[tuple[str, str | None], ...], command: str, orgao: str | None
) -> list[tuple[str, str | None]]:
    """Every later step in the plan that transitively depends on (command,
    orgao): same-órgão steps later in phase order, plus `consolidate` (which
    depends on every órgão's `report`)."""
    start = _PHASE_ORDER.index(command)
    downstream: list[tuple[str, str | None]] = []
    for later_command, later_orgao in plan:
        if later_command == "consolidate" and command != "consolidate":
            downstream.append((later_command, later_orgao))
            continue
        if later_orgao == orgao and _PHASE_ORDER.index(later_command) > start:
            downstream.append((later_command, later_orgao))
    return downstream


def execute_run(
    request: RunRequest,
    on_state_change: Callable[[CommandStateEntry], None] = _noop_state_change,
    on_failure: Callable[[CommandStateEntry], FailureDecision] = _abort_on_failure,
) -> RunResult:
    session_started_at = _now()
    plan = _plan(request.orgao)
    state = _ensure_state(request, plan)
    path = state_path(request.competencia, request.orgao, request.runs_dir)
    # Not saved here — the state file is created on demand at the first Command
    # actually dispatched (ticket "Run orchestrator and resume"), not pre-created
    # empty at Run start.

    results: list[CommandResult] = []
    skipped_steps: set[tuple[str, str | None]] = set()

    def record_failure_and_decide(
        command: str,
        orgao: str | None,
        error_message: str | None,
        *,
        started_at: str | None = None,
        finished_at: str | None = None,
    ) -> FailureDecision:
        """Build the `error` entry, persist+notify, ask `on_failure`, and — on
        `"skip"`/`"isolate"` — cascade the downstream steps too. One seam for
        both failure sites below (pre-dispatch dependency check, post-dispatch
        `Result.status == "error"`): they differ only in what triggered the
        error, never in how retry/skip/isolate/abort is handled.

        `"skip"` (a human's call, interactive mode) reclassifies the failing
        command itself to `skipped` — it's being waved off. `"isolate"` (the
        automatic non-interactive policy, ticket 08) leaves it `error` so
        `exit_code_for_run` still reports the technical failure (ticket 03),
        cascading only what depends on it."""
        nonlocal state
        entry = CommandStateEntry(
            command=command,
            orgao=orgao,
            status="error",
            started_at=started_at,
            finished_at=finished_at,
            error_message=error_message,
        )
        state = _upsert(state, entry)
        save_state(path, state)
        on_state_change(entry)
        decision = on_failure(entry)
        if decision == "skip":
            skipped_entry = CommandStateEntry(command=command, orgao=orgao, status="skipped")
            state = _upsert(state, skipped_entry)
            save_state(path, state)
            on_state_change(skipped_entry)
        if decision in ("skip", "isolate"):
            state = _cascade_skip(plan, command, orgao, state, path, on_state_change, skipped_steps)
        return decision

    for command, orgao in plan:
        if command not in request.commands:
            entry = CommandStateEntry(command=command, orgao=orgao, status="skipped")
            state = _upsert(state, entry)
            save_state(path, state)
            on_state_change(entry)
            skipped_steps.add((command, orgao))
            continue

        current = _find_entry(state, command, orgao)
        if (
            current is not None
            and current.status in ("done", "skipped")
            and not request.force
            and command not in request.force_commands
        ):
            continue
        if (command, orgao) in skipped_steps:
            continue

        while True:
            missing = dependency_missing(command, orgao, request)
            if missing:
                message = "dependência não satisfeita: " + "; ".join(missing)
                # Pre-dispatch failures are deterministic (ticket "Failure-handling
                # flow") — the real InteractionProvider never offers "retry" here,
                # it's only reachable if a caller insists, and just re-checks.
                decision = record_failure_and_decide(command, orgao, message)
                if decision == "retry":
                    continue
                if decision in ("skip", "isolate"):
                    break
                return RunResult(
                    request.competencia,
                    request.orgao,
                    tuple(results),
                    state,
                    request,
                    session_started_at,
                    _now(),
                )

            running_entry = CommandStateEntry(
                command=command,
                orgao=orgao,
                status="running",
                started_at=_now(),
            )
            state = _upsert(state, running_entry)
            save_state(path, state)
            on_state_change(running_entry)

            result = _dispatch(command, orgao, request)
            results.append(result)

            if result.status == "done":
                entry = CommandStateEntry(
                    command=command,
                    orgao=orgao,
                    status="done",
                    started_at=running_entry.started_at,
                    finished_at=_now(),
                )
                state = _upsert(state, entry)
                save_state(path, state)
                on_state_change(entry)
                break

            decision = record_failure_and_decide(
                command,
                orgao,
                result.error_message,
                started_at=running_entry.started_at,
                finished_at=_now(),
            )
            if decision == "retry":
                continue
            if decision in ("skip", "isolate"):
                break
            return RunResult(
                request.competencia,
                request.orgao,
                tuple(results),
                state,
                request,
                session_started_at,
                _now(),
            )

    return RunResult(
        request.competencia,
        request.orgao,
        tuple(results),
        state,
        request,
        session_started_at,
        _now(),
    )


def _cascade_skip(
    plan: tuple[tuple[str, str | None], ...],
    command: str,
    orgao: str | None,
    state: RunState,
    path: Path,
    on_state_change: Callable[[CommandStateEntry], None],
    skipped_steps: set[tuple[str, str | None]],
) -> RunState:
    for later_command, later_orgao in _downstream(plan, command, orgao):
        if (later_command, later_orgao) in skipped_steps:
            continue
        entry = CommandStateEntry(command=later_command, orgao=later_orgao, status="skipped")
        skipped_steps.add((later_command, later_orgao))
        state = _upsert(state, entry)
        save_state(path, state)
        on_state_change(entry)
    return state
