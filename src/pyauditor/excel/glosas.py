"""Glosa monetária: item 35 do Termo de Referência, per docs/spec/inms-pipeline.md
§12. `Ajuste_NMS(%) = min(30%, Σ Pontos_NMS × 0,001%)`, valor da glosa =
percentual × valor-base, teto de 30% com rollover do excedente para o mês
seguinte (exceto no último mês de vigência do contrato).
"""

from dataclasses import dataclass
from typing import Final

POINTS_TO_PERCENT: Final = 0.001
CAP_PCT: Final = 30.0


@dataclass(frozen=True)
class GlosaResult:
    total_points: float
    percentual_ajuste: float
    teto_atingido: bool
    valor_base: float | None
    valor_da_glosa: float | None
    # Excedente além do teto de 30%, em pontos percentuais — 0 se o teto não
    # foi atingido, ou se é o último mês de vigência (não há mês seguinte).
    saldo_rolado_pct: float


def compute_glosa(
    total_points: float, valor_base: float | None, *, is_final_month: bool = False
) -> GlosaResult:
    raw_pct = total_points * POINTS_TO_PERCENT
    percentual_ajuste = min(raw_pct, CAP_PCT)
    teto_atingido = raw_pct > CAP_PCT

    saldo_rolado_pct = 0.0
    if teto_atingido and not is_final_month:
        saldo_rolado_pct = raw_pct - CAP_PCT

    valor_da_glosa = (percentual_ajuste / 100) * valor_base if valor_base is not None else None

    return GlosaResult(
        total_points=total_points,
        percentual_ajuste=percentual_ajuste,
        teto_atingido=teto_atingido,
        valor_base=valor_base,
        valor_da_glosa=valor_da_glosa,
        saldo_rolado_pct=saldo_rolado_pct,
    )
