"""Shared target/shortfall math used by every shape with a percentage meta.

Anexo D's penalty formulas (INMS 1.1, 1.2 — see docs/spec/inms-pipeline.md
§2/§7.1) are continuous, not stepped: `(meta - resultado) / passo * pontos`,
with no rounding. There is no ceiling/floor to a whole "degrau".
"""

EPSILON = 1e-9


def meets_target(result_pct: float, operator: str, target: float) -> bool:
    if operator == '>=':
        return result_pct >= target - EPSILON
    return result_pct <= target + EPSILON


def shortfall(result_pct: float, operator: str, target: float) -> float:
    return (target - result_pct) if operator == '>=' else (result_pct - target)


def safe_pct(numerator: float, denominator: float) -> float:
    """`numerator/denominator * 100`, or 0.0 when the denominator is 0."""
    return (numerator / denominator) * 100 if denominator else 0.0


def ratio_penalty_points(
    numerator: float,
    denominator: float,
    operator: str,
    target: float,
    step_size_pct: float,
    step_points: float,
    base_points: float = 0.0,
) -> float:
    """Pontos de penalidade linear (Anexo D) de um ratio contra a meta.

    Regra única compartilhada por toda estratégia com meta percentual
    (ticket reducao-friccao/02): denominador zero — nenhuma atividade elegível
    na competência — não tem base contra a qual medir, logo é conforme e vale
    0 pontos. Nenhum chamador pode aplicar ``shortfall`` a um `safe_pct` que
    silenciosamente retornou 0.0 (esse caminho penalizava um período vazio
    como se fosse desempenho 0%).

    Sem déficit (resultado atinge a meta) vale 0 — ``base_points`` só entra
    quando há shortfall real, não só porque o indicador tem uma base.
    """
    if denominator == 0:
        return 0.0
    steps = (
        max(shortfall(safe_pct(numerator, denominator), operator, target), 0.0)
        / step_size_pct
    )
    if steps <= 0.0:
        return 0.0
    return base_points + steps * step_points
