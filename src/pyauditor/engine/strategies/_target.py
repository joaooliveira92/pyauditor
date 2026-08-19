"""Shared target/shortfall math used by every shape with a percentage meta.

Anexo D's penalty formulas (INMS 1.1, 1.2 — see docs/spec/inms-pipeline.md
§2/§7.1) are continuous, not stepped: `(meta - resultado) / passo * pontos`,
with no rounding. There is no ceiling/floor to a whole "degrau".
"""

EPSILON = 1e-9


def meets_target(result_pct: float, operator: str, target: float) -> bool:
    if operator == ">=":
        return result_pct >= target - EPSILON
    return result_pct <= target + EPSILON


def shortfall(result_pct: float, operator: str, target: float) -> float:
    return (target - result_pct) if operator == ">=" else (result_pct - target)


def safe_pct(numerator: float, denominator: float) -> float:
    """`numerator/denominator * 100`, or 0.0 when the denominator is 0."""
    return (numerator / denominator) * 100 if denominator else 0.0
