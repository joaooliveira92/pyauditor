"""Topologia do pipeline phase-major (ticket 06 SRP) — **pura**, sem efeitos.

Extraído de `orchestration/run.py`: define os comandos suportados, o ordenamento
por fase e a montagem do plano por seletor de órgão. Muda quando a topologia
muda (adicionar/remover fase ou comando) — nada mais.
"""

from __future__ import annotations

from typing import Final

__all__: Final[tuple[str, ...]] = (
    "ORGANIZATION_COMMANDS",
    "PHASE_INDEX",
    "PHASE_ORDER",
    "SUPPORTED_ORGAO_SELECTORS",
    "downstream",
    "plan",
)

ALL_COMMANDS: Final[frozenset[str]] = frozenset(
    {
        "bootstrap",
        "split",
        "measure",
        "report",
        "consolidate",
    }
)
ORGANIZATION_COMMANDS: Final[frozenset[str]] = frozenset(
    {
        "bootstrap",
        "split",
        "measure",
        "report",
    }
)
SUPPORTED_ORGAO_SELECTORS: Final[frozenset[str]] = frozenset(
    {
        "MinC",
        "MTur",
        "both",
    }
)
PHASE_ORDER: Final[tuple[str, ...]] = (
    "bootstrap",
    "split",
    "measure",
    "report",
    "consolidate",
)
PHASE_INDEX: Final[dict[str, int]] = {
    command: index
    for index, command in enumerate(PHASE_ORDER)
}


def plan(orgao_selector: str) -> tuple[tuple[str, str | None], ...]:
    """Build the phase-major execution plan."""
    if orgao_selector not in SUPPORTED_ORGAO_SELECTORS:
        raise ValueError(f"Unsupported organization selector: {orgao_selector!r}")

    organizations = ("MinC", "MTur") if orgao_selector == "both" else (orgao_selector,)

    steps: list[tuple[str, str | None]] = []

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


def downstream(
    plan: tuple[tuple[str, str | None], ...],
    command: str,
    orgao: str | None,
) -> tuple[tuple[str, str | None], ...]:
    """Return all planned steps that transitively depend on one command."""
    start_index = PHASE_INDEX.get(command)
    if start_index is None:
        raise ValueError(f"Unsupported command: {command!r}")

    downstream_steps: list[tuple[str, str | None]] = []

    for later_command, later_orgao in plan:
        later_index = PHASE_INDEX.get(later_command)
        if later_index is None:
            raise ValueError(f"Unsupported planned command: {later_command!r}")

        if later_command == "consolidate" and command != "consolidate":
            downstream_steps.append((later_command, later_orgao))
            continue

        if later_orgao == orgao and later_index > start_index:
            downstream_steps.append((later_command, later_orgao))

    return tuple(downstream_steps)
