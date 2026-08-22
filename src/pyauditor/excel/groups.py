"""Indicator -> grupo operacional mapping, per docs/spreadsheet.md §Abas 5-8.

docs/spreadsheet.md lists several indicator numbers under more than one
group tab (e.g. INMS 1.1 appears in ATENDIMENTO_N1, ATENDIMENTO_N2 and
OPERACAO_N3) — envisioning one measurement *per group* for shared services.
Where `split` (spec §14) produces one measurement per Categoria, each
derived summary is routed to its own categoria's tab by
`group_for_summary` — see that function and `categoria_from_indicator_id`.
An indicator that was never split (a `mode: whole_indicator` categoria, or
one with no categorias.yaml entry at all — e.g. INMS 1.8's catalog sum) has
only one measurement and falls back to `primary_group`, its first-listed
tab, not duplicated across every tab that mentions it.
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
    ATENDIMENTO_N1: (
        "INMS 1.1",
        "INMS 1.2",
        "INMS 1.6",
        "INMS 1.7",
        "INMS 1.11",
        "INMS 1.12",
        "INMS 1.13",
    ),
    MONITORAMENTO_NOC_SOC: ("INMS 1.4", "INMS 1.5", "INMS 1.14"),
    ATENDIMENTO_N2: ("INMS 1.1", "INMS 1.2", "INMS 1.6", "INMS 1.7", "INMS 1.9"),
    OPERACAO_N3: (
        "INMS 1.1",
        "INMS 1.2",
        "INMS 1.3",
        "INMS 1.6",
        "INMS 1.7",
        "INMS 1.9",
        "INMS 1.10",
        "INMS 1.14",
    ),
}


# The per-asset disponibilidade indicators (spec §2.1) are exactly
# MONITORAMENTO_NOC_SOC's membership — exposed here so other modules (e.g.
# excel/orgao_consolidation.py's MinC/MTur exception) don't hardcode a
# second copy of this list and risk drifting from it.
PER_ASSET_CONTRACTUAL_IDS: Final[frozenset[str]] = frozenset(
    _GROUP_MEMBERSHIP[MONITORAMENTO_NOC_SOC]
)


def primary_group(contractual_id: str) -> str | None:
    """The first group tab (in GROUP_TABS order) listing `contractual_id`.

    None if the indicator isn't on any group tab (e.g. INMS 1.8 — Anexo E's
    catalog sum isn't part of docs/spreadsheet.md's group tabs at all).
    """
    for group in GROUP_TABS:
        if contractual_id in _GROUP_MEMBERSHIP[group]:
            return group
    return None


def categoria_from_indicator_id(indicator_id: str) -> str | None:
    """The categoria key a `split`-derived indicator id encodes, if any.

    `cli/split.py`'s `_derive_config` names derived configs
    `f"{base.indicator.id}.{categoria_key}"` (e.g. `"INMS-01.ATENDIMENTO_N1"`)
    — the categoria key is always exactly a `GROUP_TABS` name (spec §14.2),
    so this doubles as validation: a dotted id whose suffix isn't a known
    tab isn't treated as categoria-derived.
    """
    if "." not in indicator_id:
        return None
    categoria_key = indicator_id.split(".", 1)[1]
    return categoria_key if categoria_key in GROUP_TABS else None


def group_for_summary(indicator_id: str, contractual_id: str) -> str | None:
    """The group tab a measurement belongs on.

    A `split`-derived measurement (module docstring — one measurement per
    Categoria, spec §14) belongs on its own categoria's tab, not on
    whichever tab `contractual_id` happens to list first; only a
    non-derived (`whole_indicator`) summary falls back to `primary_group`.
    """
    categoria = categoria_from_indicator_id(indicator_id)
    if categoria is not None:
        return categoria
    return primary_group(contractual_id)
