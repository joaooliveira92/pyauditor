"""Interpretação contratual da penalidade por degraus (INMS 1.1/1.2 — Anexo D).

A metodologia adotada é a *linear contínua* (sem arredondamento: `base +
(déficit / passo) x pontos_degrau`). O ROM expõe, além dela, as duas leituras
alternativas de degraus (completos e "qualquer fração inicia novo degrau")
para transparência — a derivação dessas três leituras é regra de negócio da
engine, não formatação: qualquer consumidor (Markdown hoje, célula no Excel
futuro) deve poder interpretar a penalidade sem recalcular `math.floor/ceil`.

Extraído de `rom/render.py` (ticket 07 SRP): o render passou a só formatar o
resultado computado aqui.
"""

import math
from dataclasses import dataclass

from pyauditor.config.models import IndicatorConfig
from pyauditor.engine.strategies._target import shortfall
from pyauditor.engine.strategies.base import CalculationResult


@dataclass(frozen=True)
class PenaltyReadings:
    """Três leituras da penalidade por degrau, em pontos."""

    linear: float
    floor: float
    ceil: float


def penalty_interpretation(
    config: IndicatorConfig,
    calculation: CalculationResult,
) -> PenaltyReadings | None:
    """Três leituras da pontuação da penalidade quando há ambiguidade
    linear-vs-degraus a divulgar.

    Devolve `None` quando não há o que interpretar: shape sem `penalty`
    (ex.: `count_difference`) ou indicador conforme (nenhuma pontuação).
    """
    if config.penalty is None or calculation.penalty_points <= 0:
        return None
    if config.target is None:
        raise ValueError(
            'penalty config sem `target` — `penalty` sempre acompanha '
            '`target` p/ ratio'
        )

    deficit = max(
        shortfall(
            calculation.result_pct, config.target.operator, config.target.value
        ),
        0.0,
    )
    steps = deficit / config.penalty.step_size_pct
    base = config.penalty.base_points
    step_points = config.penalty.step_points
    return PenaltyReadings(
        linear=calculation.penalty_points,
        floor=base + math.floor(steps) * step_points,
        ceil=base + math.ceil(steps) * step_points,
    )
