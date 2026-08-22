"""Recuperação e reconciliação do estado persistido (ticket 06 SRP).

Extraído de `orchestration/run.py`: `_ensure_state`/`_reconcile_state` —
carregar, recuperar de corrupção e reconciliar o documento `RunState` com o
plano da invocação atual. Depende de `orchestration.state` e da topologia
(`plan.PHASE_ORDER` — a ordem do estado segue a ordem por fase).
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from pyauditor.logging import logger
from pyauditor.orchestration.state import (
    CommandStateEntry,
    RunState,
    RunStateCorrupted,
    load_state,
    reset_stale_running,
    state_path,
)

__all__: Final[tuple[str, ...]] = (
    'PlannedStep',
    'ensure_state',
    'reconcile_state',
)

PlannedStep = tuple[str, str | None]


def _fresh_state(
    competencia: str,
    orgao_selector: str,
    plan: tuple[PlannedStep, ...],
) -> RunState:
    """Estado inicial: todo passo do plano como `pending`."""
    return RunState(
        competencia=competencia,
        orgao_selector=orgao_selector,
        commands=tuple(
            CommandStateEntry(
                command=command,
                orgao=orgao,
                status='pending',
            )
            for command, orgao in plan
        ),
    )


def reconcile_state(
    existing: RunState,
    competencia: str,
    orgao_selector: str,
    runs_dir: Path,
    plan: tuple[PlannedStep, ...],
) -> RunState:
    """Reconcile persisted command state with the current execution plan.

    Obsolete entries are removed. Existing entries belonging to the current
    plan are preserved and reordered according to the current phase-major
    plan. Missing entries are initialized as ``pending``.
    """
    if existing.competencia != competencia:
        raise RunStateCorrupted(
            state_path(
                competencia,
                orgao_selector,
                runs_dir,
            ),
            'persisted competencia does not match the current request',
        )

    if existing.orgao_selector != orgao_selector:
        raise RunStateCorrupted(
            state_path(
                competencia,
                orgao_selector,
                runs_dir,
            ),
            'persisted orgao_selector does not match the current request',
        )

    reset_state = reset_stale_running(existing)
    entries = {
        (entry.command, entry.orgao): entry for entry in reset_state.commands
    }

    commands = tuple(
        entries.get(
            (command, orgao),
            CommandStateEntry(
                command=command,
                orgao=orgao,
                status='pending',
            ),
        )
        for command, orgao in plan
    )

    return RunState(
        competencia=competencia,
        orgao_selector=orgao_selector,
        commands=commands,
    )


def ensure_state(
    competencia: str,
    orgao_selector: str,
    runs_dir: Path,
    plan: tuple[PlannedStep, ...],
) -> RunState:
    """Load, recover, and reconcile persisted orchestration state."""
    path = state_path(
        competencia,
        orgao_selector,
        runs_dir,
    )

    try:
        existing = load_state(path)
    except RunStateCorrupted as exc:
        logger.warning(
            '%s; starting the run from filesystem state',
            exc,
        )
        existing = None

    if existing is None:
        return _fresh_state(competencia, orgao_selector, plan)

    try:
        return reconcile_state(
            existing,
            competencia,
            orgao_selector,
            runs_dir,
            plan,
        )
    except RunStateCorrupted as exc:
        logger.warning(
            '%s; starting the run from filesystem state',
            exc,
        )
        return _fresh_state(competencia, orgao_selector, plan)
