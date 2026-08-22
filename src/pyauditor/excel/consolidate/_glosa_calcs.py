"""Aritmética pura da glosa consolidada — **sem** `openpyxl`.

Extraído de `excel/consolidate.py` (ticket 04 SRP): o `build_glosas` misturava
no mesmo corpo deduplicação de resumo, acúmulo de pontos por órgão, decisão
de anistia, rateio do saldo anterior, `compute_glosa` e a escrita das linhas.
A agregação vive aqui, testável sem workbook; o builder renderiza o resultado.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from pyauditor.codes import format_inms_code
from pyauditor.excel.glosas import (
    CAP_PCT,
    POINTS_TO_PERCENT,
    Historico,
    compute_glosa,
    saldo_anterior_pct_de,
)
from pyauditor.rom.dedup import deduplicate_summaries
from pyauditor.rom.summary import IndicatorSummary

__all__: Final[tuple[str, ...]] = (
    "GlosaAggregation",
    "accumulate_pontos_por_orgao",
    "compute_aggregation",
)

_DECISAO_ACEITA: Final[str] = "aceita"


def is_amnestied(decision: dict[str, object]) -> bool:
    """O fiscal aceitou a justificativa do fornecedor (`Decisão Fiscal`
    começando com "aceita") → ocorrência sai da base de pontos."""
    return (
        str(decision.get("Decisão Fiscal") or "").strip().lower().startswith(_DECISAO_ACEITA)
    )


@dataclass(frozen=True)
class GlosaAggregation:
    """Pontos/glosa consolidados, prontos para uma linha de resumo (aviso:
    `total_pontos`/`glosa_final` são a soma das glosas por-órgão)."""

    pontos_por_orgao: dict[str, float]
    total_pontos: float
    glosa_final: float
    pct_bruto: float
    aplicado: float


def accumulate_pontos_por_orgao(
    minc: list[IndicatorSummary],
    mtur: list[IndicatorSummary],
    existing_decisions: dict[tuple[str, str], dict[str, object]],
) -> tuple[dict[str, float], set[tuple[str, str]]]:
    """Soma os pontos de glosa por órgão, respeitando a anistia fiscal
    (`Decisão Fiscal` começando com "aceita" tira a ocorrência da base).

    Devolve ``(pontos_por_orgao, seen_keys)`` — *seen_keys* contém os
    (indicador_formatado, órgão) com ocorrência; o chamador usa para detectar
    decisões órfãs no workbook anterior.
    """
    pontos_por_orgao: dict[str, float] = {"MinC": 0.0, "MTur": 0.0}
    seen_keys: set[tuple[str, str]] = set()

    for summary in deduplicate_summaries(minc) + deduplicate_summaries(mtur):
        if summary.penalty_points <= 0:
            continue
        key = (format_inms_code(summary.contractual_id), summary.orgao)
        seen_keys.add(key)
        decision = existing_decisions.get(key, {})
        if not is_amnestied(decision):
            pontos_por_orgao[summary.orgao] = (
                pontos_por_orgao.get(summary.orgao, 0.0) + summary.penalty_points
            )
    return pontos_por_orgao, seen_keys


def compute_aggregation(
    *,
    pontos_por_orgao: dict[str, float],
    valor_base: float | None,
    competencia: str,
    historico: Historico | None,
    is_final_month: bool,
) -> GlosaAggregation:
    """Rateio do saldo anterior proporcional aos pontos + `compute_glosa`
    por-órgão + soma contra teto — a derivação financeira do resumo agregado."""
    historico = historico or {}
    saldo_anterior = saldo_anterior_pct_de(historico, competencia)
    total_pontos_bruto = sum(pontos_por_orgao.values())
    if total_pontos_bruto > 0:
        saldo_minc = saldo_anterior * (pontos_por_orgao.get("MinC", 0.0) / total_pontos_bruto)
        saldo_mtur = saldo_anterior * (pontos_por_orgao.get("MTur", 0.0) / total_pontos_bruto)
    else:
        saldo_minc = saldo_mtur = 0.0

    glosa_minc = compute_glosa(
        pontos_por_orgao.get("MinC", 0.0),
        valor_base,
        is_final_month=is_final_month,
        saldo_anterior_pct=saldo_minc,
    )
    glosa_mtur = compute_glosa(
        pontos_por_orgao.get("MTur", 0.0),
        valor_base,
        is_final_month=is_final_month,
        saldo_anterior_pct=saldo_mtur,
    )
    total_pontos = glosa_minc.total_points + glosa_mtur.total_points
    glosa_final = (glosa_minc.valor_da_glosa or 0.0) + (glosa_mtur.valor_da_glosa or 0.0)
    pct_bruto = total_pontos * POINTS_TO_PERCENT + saldo_anterior
    aplicado = min(pct_bruto, CAP_PCT)
    return GlosaAggregation(
        pontos_por_orgao=pontos_por_orgao,
        total_pontos=total_pontos,
        glosa_final=glosa_final,
        pct_bruto=pct_bruto,
        aplicado=aplicado,
    )