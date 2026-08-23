"""Testes unitários de `penalty_interpretation` (leituras linear/degrau)."""

from pyauditor.config.models import (
    ColumnEquals,
    Indicator,
    IndicatorConfig,
    Penalty,
    QualityGates,
    RatioCalculation,
    Scope,
    Source,
    Target,
)
from pyauditor.engine.strategies.base import CalculationResult
from pyauditor.engine.strategies.penalty import penalty_interpretation


def _config(penalty: Penalty | None, target: Target | None) -> IndicatorConfig:
    return IndicatorConfig(
        indicator=Indicator(
            id='INMS-1.1', contractual_id='INMS 1.1', name='Teste'
        ),
        scope=Scope(),
        source=Source(dataset='data.csv'),
        quality_gates=QualityGates(),
        calculation=RatioCalculation(
            shape='ratio',
            aggregation='count_distinct',
            numerator_filter=ColumnEquals(column='S', equals='S'),
        ),
        target=target,
        penalty=penalty,
    )


def test_penalty_interpretation_returns_none_without_penalty() -> None:
    cfg = _config(penalty=None, target=Target(operator='>=', value=90.0))
    calculation = CalculationResult(
        result_pct=50.0, conforms=False, penalty_points=10.0, memoria={}
    )
    assert penalty_interpretation(cfg, calculation) is None


def test_penalty_interpretation_returns_none_when_conforming() -> None:
    cfg = _config(
        penalty=Penalty(base_points=0, step_points=20, step_size_pct=0.1),
        target=Target(operator='>=', value=90.0),
    )
    calculation = CalculationResult(
        result_pct=95.0, conforms=True, penalty_points=0.0, memoria={}
    )
    assert penalty_interpretation(cfg, calculation) is None


def test_penalty_interpretation_reads_linear_floor_ceil() -> None:
    cfg = _config(
        penalty=Penalty(base_points=0, step_points=20, step_size_pct=0.1),
        target=Target(operator='>=', value=90.0),
    )
    calculation = CalculationResult(
        result_pct=50.0, conforms=False, penalty_points=8000.0, memoria={}
    )
    readings = penalty_interpretation(cfg, calculation)
    assert readings is not None
    assert readings.linear == 8000.0
    # shortfall = 40 p.p.; 40/0.1 = 400 degraus completos.
    assert readings.floor == 8000.0
    assert readings.ceil == 8000.0
