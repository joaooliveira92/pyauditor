"""Catálogo e política de comandos interativos (ticket 05 SRP) — fora de
`interactive/flow.py`.

Extraído de `flow.py`: quais comandos existem, seus rótulos, a
disponibilidade de `consolidate` (só `both`) e a política de re-execução
(`report`/`consolidate` sempre forçados quando selecionados).
"""

from __future__ import annotations

from typing import Final

__all__: Final[tuple[str, ...]] = (
    "ALL_COMMANDS",
    "COMMAND_LABELS",
    "force_commands_for",
)

ALL_COMMANDS: Final[tuple[str, ...]] = (
    "bootstrap",
    "split",
    "measure",
    "report",
    "consolidate",
)

COMMAND_LABELS: Final[dict[str, str]] = {
    "bootstrap": "bootstrap: cria ou atualiza a capa do contrato",
    "split": "split: prepara categorias e gera o arquivo sintético",
    "measure": "measure: apura os indicadores INMS",
    "report": "report: gera o relatório da competência",
    "consolidate": ("consolidate: reúne MinC e MTur no relatório consolidado"),
}


def force_commands_for(
    orgao: str,
    commands: frozenset[str],
) -> frozenset[str]:
    """Return applicable production commands that require fresh results.

    Report and consolidation are inexpensive to regenerate from materialized
    inputs and provide publication and financial fields required by the final
    summary. Only commands selected by the user and applicable to the current
    organization plan are forced.
    """
    forced: set[str] = set()

    if "report" in commands:
        forced.add("report")

    if orgao == "both" and "consolidate" in commands:
        forced.add("consolidate")

    return frozenset(forced)