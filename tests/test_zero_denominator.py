"""Regra de denominador zero: sem atividade elegível na competência, nenhuma
estratégia de ratio pode penalizar como não-conformidade (ticket 02).

Regressão do bug em que `segmented_ratio` confiava em `safe_pct` retornando
0.0 e aplicava `shortfall(0.0, …)`, marcando penalidade para uma categoria sem
linhas — enquanto `ratio` já tratava denominador zero como sem-período.
"""

from pyauditor.config.models import (
    ColumnEquals,
    Indicator,
    IndicatorConfig,
    Penalty,
    QualityGates,
    RatioCalculation,
    SegmentedCategory,
    SegmentedRatioCalculation,
    Source,
    Target,
)
from pyauditor.engine.strategies.ratio import RatioStrategy
from pyauditor.engine.strategies.segmented_ratio import SegmentedRatioStrategy


def _source() -> Source:
    return Source(dataset='data.csv')


def test_ratio_zero_denominator_is_conforming_with_zero_penalty() -> None:
    config = IndicatorConfig(
        indicator=Indicator(
            id='INMS-1.1', contractual_id='INMS 1.1', name='Teste'
        ),
        source=_source(),
        quality_gates=QualityGates(),
        calculation=RatioCalculation(
            shape='ratio',
            aggregation='count_distinct',
            numerator_filter=ColumnEquals(column='No prazo', equals='S'),
            denominator_filter=ColumnEquals(column='SLA', equals='Alta'),
        ),
        target=Target(operator='>=', value=90.0),
        penalty=Penalty(base_points=0, step_points=20, step_size_pct=0.1),
    )
    # Nenhuma linha casa o filtro de denominador -> sem atividade elegível.
    rows = [{'SLA': 'Baixa', 'No prazo': 'S'}]

    result = RatioStrategy().calculate(config, rows)

    assert result.conforms is True
    assert result.penalty_points == 0.0
    assert result.result_pct == 0.0


def test_segmented_ratio_zero_denominator_category_is_not_penalized() -> None:
    config = IndicatorConfig(
        indicator=Indicator(
            id='INMS-1.2', contractual_id='INMS 1.2', name='Teste'
        ),
        source=_source(),
        quality_gates=QualityGates(),
        calculation=SegmentedRatioCalculation(
            shape='segmented_ratio',
            step_size_pct=0.1,
            categories=[
                SegmentedCategory(
                    name='alta',
                    denominator_filter=ColumnEquals(
                        column='SLA', equals='Alta'
                    ),
                    numerator_filter=ColumnEquals(
                        column='No prazo', equals='S'
                    ),
                    step_points=20,
                )
            ],
        ),
        target=Target(operator='>=', value=90.0),
    )
    # Zero linhas casam o filtro de denominador -> categoria sem atividade.
    rows = [{'SLA': 'Baixa', 'No prazo': 'S'}]

    result = SegmentedRatioStrategy().calculate(config, rows)

    categories = result.memoria['categories']
    assert isinstance(categories, list)
    assert categories[0]['denominator'] == 0
    assert categories[0]['penalty_points'] == 0.0
    assert result.penalty_points == 0.0
    assert result.conforms is True
