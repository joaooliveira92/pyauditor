"""Indicator -> grupo operacional mapping, per docs/spreadsheet.md §Abas 5-8.

docs/spreadsheet.md lists several indicator numbers under more than one
group tab (e.g. INMS 1.1 appears in ATENDIMENTO_N1, ATENDIMENTO_N2 and
OPERACAO_N3) — envisioning one measurement *per group* for shared services.
That's not what the engine measures: each contractual indicator number has
exactly one YAML+CSV pair, one measurement, no group dimension in the
schema (tickets 02-07). Until multiple measurements per indicator number
exist (fog — see spec.md §13), each indicator is placed on its first-listed
group tab only, not duplicated across every tab that mentions it.
"""

from typing import Final

ATENDIMENTO_N1: Final = "ATENDIMENTO_N1"
MONITORAMENTO_NOC_SOC: Final = "MONITORAMENTO_NOC_SOC"
ATENDIMENTO_N2: Final = "ATENDIMENTO_N2"
OPERACAO_N3: Final = "OPERACAO_N3"

GROUP_TABS: Final[tuple[str, ...]] = (
    ATENDIMENTO_N1,
    MONITORAMENTO_NOC_SOC,
    ATENDIMENTO_N2,
    OPERACAO_N3,
)

# docs/spreadsheet.md §Abas 5-8, in tab order — first match wins (see module docstring).
_GROUP_MEMBERSHIP: Final[dict[str, tuple[str, ...]]] = {
    ATENDIMENTO_N1: ("INMS 1.1", "INMS 1.2", "INMS 1.6", "INMS 1.7", "INMS 1.11", "INMS 1.12", "INMS 1.13"),
    MONITORAMENTO_NOC_SOC: ("INMS 1.4", "INMS 1.5", "INMS 1.14"),
    ATENDIMENTO_N2: ("INMS 1.1", "INMS 1.2", "INMS 1.6", "INMS 1.7", "INMS 1.9"),
    OPERACAO_N3: ("INMS 1.1", "INMS 1.2", "INMS 1.3", "INMS 1.6", "INMS 1.7", "INMS 1.9", "INMS 1.10", "INMS 1.14"),
}


def primary_group(contractual_id: str) -> str | None:
    """The first group tab (in GROUP_TABS order) listing `contractual_id`.

    None if the indicator isn't on any group tab (e.g. INMS 1.8 — Anexo E's
    catalog sum isn't part of docs/spreadsheet.md's group tabs at all).
    """
    for group in GROUP_TABS:
        if contractual_id in _GROUP_MEMBERSHIP[group]:
            return group
    return None
