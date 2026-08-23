"""`derive_config` (cli/split_derive.py) é a única regra de derivação de
config por Categoria — usada tanto pelo caminho materializado (`split`)
quanto pelo caminho em memória (`measure`, `cli/measure.py`). Ver
ADR-0003: os dois caminhos devem produzir o mesmo `IndicatorConfig`
derivado, exceto `source` (materializado aponta pro CSV filtrado em disco;
em memória mantém o `source` do indicador base)."""

from pyauditor.cli.split_derive import derive_config
from pyauditor.config.acceptance import AcceptanceTest, RatioAcceptanceExpected
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

_BASE_CONFIG = IndicatorConfig(
    indicator=Indicator(
        id='INMS-01',
        contractual_id='INMS 1.1',
        name='Indicador sintético',
    ),
    scope=Scope(contract='40/2022'),
    source=Source(csv='inms-01.csv', delimiter=';', id_column='ID'),
    quality_gates=QualityGates(),
    calculation=RatioCalculation(
        shape='ratio',
        aggregation='count_distinct',
        numerator_filter=ColumnEquals(column='No prazo', equals='S'),
    ),
    target=Target(operator='>=', value=98.0),
    penalty=Penalty(base_points=100, step_points=10, step_size_pct=1.0),
    acceptance_test=AcceptanceTest(
        expected=RatioAcceptanceExpected(
            shape='ratio',
            numerator=98.0,
            denominator=100.0,
            result_pct=98.0,
            conforms=True,
            penalty_points=0.0,
        )
    ),
)


def test_derive_config_in_memory_keeps_base_source() -> None:
    """Caminho em memória (measure): `csv_relpath` omitido — `source`
    permanece o de *base*, já que não há CSV filtrado em disco."""
    derived = derive_config(_BASE_CONFIG, 'N1')

    assert derived.indicator.id == 'INMS-01.N1'
    assert derived.source == _BASE_CONFIG.source
    assert derived.acceptance_test is None
    assert derived.quality_gates == _BASE_CONFIG.quality_gates
    assert derived.calculation == _BASE_CONFIG.calculation
    assert derived.target == _BASE_CONFIG.target
    assert derived.penalty == _BASE_CONFIG.penalty


def test_derive_config_materialized_points_at_filtered_csv() -> None:
    """Caminho materializado (split): `csv_relpath`/`delimiter` apontam a
    config derivada pro CSV filtrado em disco, preservando id_column e
    period_column de *base*."""
    derived = derive_config(
        _BASE_CONFIG,
        'N1',
        '_split/INMS-01/N1.csv',
        ';',
    )

    assert derived.indicator.id == 'INMS-01.N1'
    assert derived.source.csv == '_split/INMS-01/N1.csv'
    assert derived.source.dataset is None
    assert derived.source.id_column == _BASE_CONFIG.source.id_column
    assert derived.acceptance_test is None


def test_derive_config_both_paths_agree_except_source() -> None:
    """Regressão do risco documentado no ADR-0003: os dois caminhos de
    derivação não devem divergir em nada além de `source`."""
    in_memory = derive_config(_BASE_CONFIG, 'N1')
    materialized = derive_config(
        _BASE_CONFIG, 'N1', '_split/INMS-01/N1.csv', ';'
    )

    in_memory_dump = in_memory.model_dump(mode='json', exclude={'source'})
    materialized_dump = materialized.model_dump(
        mode='json', exclude={'source'}
    )
    assert in_memory_dump == materialized_dump
