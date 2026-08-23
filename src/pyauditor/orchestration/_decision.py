"""Máquina de decisão de falha do orquestrador (ticket 05 SRP).

Conceitos de decisão isolados de `orchestration/run.py`: o tipo
`FailureDecision`, as políticas (`isolate_on_failure`, `_abort_on_failure`),
a validação da decisão e o encadeamento de falha (`handle_failure` +
`_cascade_skip`). `handle_failure` registra a entrada em ``error``, decide
com o callback `on_failure`, aplica `skip`/`isolate` (incl. cascade para as
etapas dependentes) e devolve o estado atualizado — sem `nonlocal`.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Final, Literal, cast

from pyauditor.orchestration._flow_helpers import (
    find_entry,
    notify_state_change,
    now,
    sanitize_error_message,
    upsert,
)
from pyauditor.orchestration.plan import downstream
from pyauditor.orchestration.state import (
    CommandStateEntry,
    RunState,
    save_state,
)

__all__: tuple[str, ...] = (
    'FailureDecision',
    'handle_failure',
    'isolate_on_failure',
)

type FailureDecision = Literal[
    'retry',
    'skip',
    'isolate',
    'abort',
]

type PlanStep = tuple[str, str | None]

_FAILURE_DECISIONS: Final[frozenset[str]] = frozenset(
    {
        'retry',
        'skip',
        'isolate',
        'abort',
    }
)

_FAILURE_REASON_FALLBACK: Final[str] = 'comando terminou com erro sem mensagem'
_CASCADE_REASON_FALLBACK: Final[str] = 'etapa ignorada por falha anterior'


def _abort_on_failure(_entry: CommandStateEntry) -> FailureDecision:
    """Abort after the first command failure."""
    return 'abort'


def isolate_on_failure(
    _entry: CommandStateEntry,
) -> FailureDecision:
    """Isolate a failed organization while preserving technical failure.

    The failed command remains in ``error`` state so the aggregate exit code
    reports a technical failure. Later commands for the same organization and
    the shared consolidation are marked ``skipped``. Commands belonging to
    another organization remain eligible to run.
    """
    return 'isolate'


def _validate_failure_decision(
    decision: object,
) -> FailureDecision:
    """Validate a decision returned by the failure callback."""
    if not isinstance(decision, str):
        raise TypeError(
            f'on_failure must return a string decision, received'
            f'{type(decision).__name__}'
        )

    if decision not in _FAILURE_DECISIONS:
        raise ValueError(
            f'on_failure returned an unsupported decision: {decision!r}'
        )

    return cast(FailureDecision, decision)


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
    for later_command, later_orgao in downstream(
        plan,
        command,
        orgao,
    ):
        step = (later_command, later_orgao)
        if step in skipped_steps:
            continue

        current = find_entry(
            state,
            later_command,
            later_orgao,
        )
        if current is not None and current.status == 'done':
            continue

        entry = CommandStateEntry(
            command=later_command,
            orgao=later_orgao,
            status='skipped',
            finished_at=now(),
            error_message=sanitize_error_message(
                reason,
                fallback=_CASCADE_REASON_FALLBACK,
            ),
        )
        skipped_steps.add(step)
        state = upsert(state, entry)
        save_state(path, state)
        notify_state_change(on_state_change, entry)

    return state


def handle_failure(
    state: RunState,
    *,
    command: str,
    orgao: str | None,
    error_message: str | None,
    started_at: str,
    finished_at: str,
    plan: tuple[PlanStep, ...],
    path: Path,
    on_state_change: Callable[[CommandStateEntry], None],
    on_failure: Callable[[CommandStateEntry], FailureDecision],
    skipped_steps: set[PlanStep],
) -> tuple[RunState, FailureDecision]:
    """Persist a command as ``error``, apply the failure decision and return
    the updated state plus the decision. ``'retry'`` keeps the caller in the
    dispatch loop; ``'skip'``/``'isolate'`` trigger the dependency cascade;
    ``'abort'`` stops the run (the error remains persisted)."""
    safe_message = sanitize_error_message(
        error_message,
        fallback=_FAILURE_REASON_FALLBACK,
    )
    error_entry = CommandStateEntry(
        command=command,
        orgao=orgao,
        status='error',
        started_at=started_at,
        finished_at=finished_at,
        error_message=safe_message,
    )
    state = upsert(state, error_entry)
    save_state(path, state)
    notify_state_change(
        on_state_change,
        error_entry,
    )

    decision = _validate_failure_decision(on_failure(error_entry))

    if decision == 'skip':
        skipped_entry = CommandStateEntry(
            command=command,
            orgao=orgao,
            status='skipped',
            finished_at=now(),
            error_message=safe_message,
        )
        state = upsert(state, skipped_entry)
        save_state(path, state)
        notify_state_change(
            on_state_change,
            skipped_entry,
        )

    if decision in {'skip', 'isolate'}:
        state = _cascade_skip(
            plan,
            command,
            orgao,
            state,
            path,
            on_state_change,
            skipped_steps,
            reason=(
                f'etapa dependente de {command} ({orgao or "global"}) não '
                f'executada'
            ),
        )

    return state, decision
