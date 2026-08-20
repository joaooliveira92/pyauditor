"""MinC/MTur consolidation for `INMS_BASE`, per docs/spreadsheet.md:

    Resultado consolidado = (Numerador MinC + Numerador MTur) / (Denominador MinC + Denominador MTur)

Used by `excel/consolidate.py`'s `consolidate` subcommand (2.1), which is the
only place MinC and MTur summaries are ever combined — `report.py` is
per-órgão by construction and never calls this (.scratch/multi-org-pipeline
ticket 02). Only affects `INMS_BASE`'s view — `consolidate.py`'s GLOSAS keeps
one row per (indicador × órgão), so this never double-counts penalty points.

Scope: `docs/spreadsheet.md` calls out an exception for per-asset
disponibilidade indicators (1.4/1.5/1.14) — "o consolidado deverá seguir a
fórmula específica prevista no Termo de Referência" — which isn't identified
in any read primary source. Those 3 stay un-consolidated (one row per órgão)
rather than risk applying the wrong formula.
"""

from dataclasses import replace
from typing import Final

from pyauditor.excel.groups import PER_ASSET_CONTRACTUAL_IDS
from pyauditor.rom.summary import IndicatorSummary

_CONSOLIDATABLE_SHAPES: Final[frozenset[str]] = frozenset({"ratio", "segmented_ratio", "count_difference"})

# Mirrors engine/strategies/_target.py's tolerance. Duplicated rather than
# imported: that module is package-private (leading underscore) to
# `engine.strategies`, and `excel` reaching into it for two lines of float
# comparison isn't worth crossing that boundary for.
_EPSILON: Final = 1e-9


def with_orgao_consolidation(summaries: list[IndicatorSummary]) -> list[IndicatorSummary]:
    """Original summaries, plus one synthetic "Consolidado" row per
    indicator/asset where both MinC and MTur measured it.
    """
    by_key: dict[tuple[str, str | None], dict[str, IndicatorSummary]] = {}
    for summary in summaries:
        by_key.setdefault((summary.contractual_id, summary.asset), {})[summary.orgao] = summary

    rows = list(summaries)
    for (contractual_id, _asset), by_orgao in by_key.items():
        if contractual_id in PER_ASSET_CONTRACTUAL_IDS:
            continue
        minc = by_orgao.get("MinC")
        mtur = by_orgao.get("MTur")
        if minc is None or mtur is None:
            continue

        consolidated = _consolidate(minc, mtur)
        if consolidated is not None:
            rows.append(consolidated)

    return rows


def _consolidate(minc: IndicatorSummary, mtur: IndicatorSummary) -> IndicatorSummary | None:
    if minc.shape not in _CONSOLIDATABLE_SHAPES:
        return None
    if minc.numerator is None or minc.denominator is None:
        return None
    if mtur.numerator is None or mtur.denominator is None:
        return None

    pooled_numerator = minc.numerator + mtur.numerator
    pooled_denominator = minc.denominator + mtur.denominator
    result_pct = (pooled_numerator / pooled_denominator) * 100 if pooled_denominator else 0.0
    conforms = _meets_target(result_pct, minc.target_operator, minc.target_value)

    return replace(
        minc,
        indicator_id=f"{minc.indicator_id}-CONSOLIDADO",
        orgao="Consolidado",
        numerator=pooled_numerator,
        denominator=pooled_denominator,
        result_pct=result_pct,
        conforms=conforms,
        # Soma direta das penalidades já computadas por órgão — o Termo de
        # Referência não define uma regra própria de penalidade para o
        # resultado consolidado; isto não é uma reaplicação da fórmula de
        # degrau sobre o percentual consolidado, só a soma do que já foi
        # apurado independentemente por órgão.
        penalty_points=minc.penalty_points + mtur.penalty_points,
    )


def _meets_target(result_pct: float, operator: str | None, target: float | None) -> bool:
    if operator is None or target is None:
        return False
    if operator == ">=":
        return result_pct >= target - _EPSILON
    return result_pct <= target + _EPSILON
