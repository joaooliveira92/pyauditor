"""Regra única da aba `INMS_BASE` (ticket 08): `report.xlsx` (26 colunas) e
`consolidado.xlsx` (15 colunas) derivam de uma única linha — fonte única para
"Conforme"/"Não conforme", `round(result_pct, 2)` e `Diferença para a meta`,
cada renderer mantendo seu próprio shape de colunas.

Antes havia dois `_inms_base_row` verbatim recomputando os mesmos conceitos
com diferença de sinal na meta (`_compliance_margin` no report, `target_value -
result_pct` no consolidate). Uma mudança no critério de "Conforme" tocava dois
lugares; agora toca um só.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from pyauditor.codes import format_inms_code
from pyauditor.excel._style import UNIT_BY_SHAPE as _UNIT_BY_SHAPE
from pyauditor.rom.summary import IndicatorSummary

__all__: Final[tuple[str, ...]] = ("InmsRowFields", "compliance_margin", "inms_base_fields")


def compliance_margin(result: float, target: float | None, operator: str | None) -> float | None:
    """Distance from the target boundary — positive in the noncompliant
    direction, how far the result must move to reach the target (from
    `excel/report.py`, now the single rule shared with consolidate).

    Returns:
        The target distance, or ``None`` when no target is configured.

    Raises:
        ValueError: If a target exists but its operator is missing or
            unsupported.
    """
    if target is None:
        return None

    if operator in {">", ">="}:
        return target - result

    if operator in {"<", "<="}:
        return result - target

    if operator in {"=", "=="}:
        return abs(result - target)

    raise ValueError(f"Unsupported target operator for compliance margin: {operator!r}.")


@dataclass(frozen=True, slots=True)
class InmsRowFields:
    """Regra única por coluna da aba `INMS_BASE` (ticket 08)."""

    competencia: str
    servico: str | None
    grupo_operacional: str | None
    codigo_inms: str
    descricao: str
    orgao: str
    meta: float | None
    sentido: str | None
    numerador: float | None
    denominador: float | None
    resultado: float
    unidade: str
    conformidade: str
    diferenca: float | None


def inms_base_fields(
    summary: IndicatorSummary,
    competencia: str,
    *,
    grupo_operacional: str | None,
) -> InmsRowFields:
    """Compute the shared `INMS_BASE` row values for one `IndicatorSummary`.

    ``grupo_operacional`` é renderer-specific (report o computa por categoria,
    consolidate usa `None`) e fica como parâmetro para a regra ser de fato uma
    função única; o restante dos campos é derivado aquí.
    """
    margin = compliance_margin(summary.result_pct, summary.target_value, summary.target_operator)
    return InmsRowFields(
        competencia=competencia,
        servico=summary.asset,
        grupo_operacional=grupo_operacional,
        codigo_inms=format_inms_code(summary.contractual_id),
        descricao=summary.name,
        orgao=summary.orgao,
        meta=summary.target_value,
        sentido=summary.target_operator,
        numerador=summary.numerator,
        denominador=summary.denominator,
        resultado=round(summary.result_pct, 2),
        unidade=_UNIT_BY_SHAPE.get(summary.shape, ""),
        conformidade="Conforme" if summary.conforms else "Não conforme",
        diferenca=round(margin, 2) if margin is not None else None,
    )
