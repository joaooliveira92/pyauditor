"""Achata um `MeasurementResult` num sumário serializável e independente de
shape — o homólogo estruturado do Markdown do ROM, consumido por `report`
(ticket 09) para montar o Excel consolidado sem re-parse do Markdown.
"""

from dataclasses import asdict, dataclass, fields
from typing import cast

from pyauditor.engine.pipeline import MeasurementResult
from pyauditor.engine.strategies import SHAPE_REGISTRY, ShapeMemoria

_STR_FIELDS: tuple[str, ...] = (
    'indicator_id',
    'contractual_id',
    'name',
    'orgao',
    'shape',
)
_OPTIONAL_STR_FIELDS: tuple[str, ...] = ('asset', 'target_operator')
_NUMERIC_FIELDS: tuple[str, ...] = ('result_pct', 'penalty_points')
_OPTIONAL_NUMERIC_FIELDS: tuple[str, ...] = (
    'target_value',
    'numerator',
    'denominator',
    'dropped_out_of_period',
    'undated_dropped',
    'ragged_rows',
    'unparseable_numerics',
)
_BOOL_FIELDS: tuple[str, ...] = (
    'conforms',
    'hard_failure',
    'systematic_failure',
)


@dataclass(frozen=True)
class IndicatorSummary:
    """Faz ida-e-volta pelo JSON (`to_dict()` / `IndicatorSummary(**raw)`) como
    sidecar que `report`/`consolidate` relê — um sidecar obsoleto ou editado à
    mão com campo de tipo errado é rejeitado aqui, no load, em vez de quebrar
    lá no fundo da aritmética de `excel/report.py`/`excel/consolidate.py`."""

    indicator_id: str
    contractual_id: str
    name: str
    asset: str | None
    orgao: str
    shape: str
    target_operator: str | None
    target_value: float | None
    result_pct: float
    conforms: bool
    penalty_points: float
    numerator: float | None
    denominator: float | None
    hard_failure: bool
    systematic_failure: bool = False
    # Filtro de período (spec competencia-cli-equipe §5): None quando o
    # filtro não rodou — sidecar antigo carrega pelos defaults, e o
    # consolidado ignora os campos por ora.
    dropped_out_of_period: int | None = None
    undated_dropped: int | None = None
    # Anomalias de leitura: 0 sem anomalia; None em sidecar legado. Ficam no
    # JSON para o consolidado poder exibir sem re-parse do Markdown.
    ragged_rows: int | None = None
    unparseable_numerics: int | None = None

    def __post_init__(self) -> None:
        known_fields = {f.name for f in fields(self)}
        for name in _STR_FIELDS:
            if name not in known_fields:
                raise AssertionError(
                    f'campo esperado `{name}` ausente do summary dataclass'
                )
            _require_str(self, name)
        for name in _OPTIONAL_STR_FIELDS:
            _require_str(self, name, optional=True)
        for name in _NUMERIC_FIELDS:
            _require_numeric(self, name)
        for name in _OPTIONAL_NUMERIC_FIELDS:
            _require_numeric(self, name, optional=True)
        for name in _BOOL_FIELDS:
            _require_bool(self, name)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _require_str(
    summary: 'IndicatorSummary', name: str, *, optional: bool = False
) -> None:
    value: object = getattr(summary, name)
    if optional and value is None:
        return
    if not isinstance(value, str):
        raise TypeError(
            f'IndicatorSummary.{name} must be str, got {type(value).__name__}'
        )


def _require_numeric(
    summary: 'IndicatorSummary', name: str, *, optional: bool = False
) -> None:
    import math

    value: object = getattr(summary, name)
    if optional and value is None:
        return
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError(
            f'IndicatorSummary.{name} must be a number, got '
            f'{type(value).__name__}'
        )
    if not math.isfinite(float(value)):
        raise ValueError(
            f'IndicatorSummary.{name} não finito ({value!r}) — sidecar '
            f'JSON com NaN/Infinity'
        )


def _require_bool(summary: 'IndicatorSummary', name: str) -> None:
    value: object = getattr(summary, name)
    if not isinstance(value, bool):
        raise TypeError(
            f'IndicatorSummary.{name} must be bool, got {type(value).__name__}'
        )


def summarize(result: MeasurementResult) -> IndicatorSummary:
    config = result.config
    calculation = result.calculation
    shape = config.calculation.shape

    numerator, denominator = _pooled_numerator_denominator(
        shape, calculation.memoria
    )

    return IndicatorSummary(
        indicator_id=config.indicator.id,
        contractual_id=config.indicator.contractual_id,
        name=config.indicator.name,
        asset=config.indicator.asset,
        orgao=config.scope.orgao,
        shape=shape,
        target_operator=config.target.operator
        if config.target is not None
        else None,
        target_value=config.target.value if config.target is not None else None,
        result_pct=calculation.result_pct,
        conforms=calculation.conforms,
        penalty_points=calculation.penalty_points,
        numerator=numerator,
        denominator=denominator,
        hard_failure=result.hard_failure,
        systematic_failure=result.systematic_failure,
        dropped_out_of_period=result.dropped_out_of_period,
        undated_dropped=result.undated_dropped,
        ragged_rows=result.ragged_rows,
        unparseable_numerics=result.unparseable_numerics,
    )


def _pooled_numerator_denominator(
    shape: str, memoria: ShapeMemoria
) -> tuple[float | None, float | None]:
    """Delega para a própria strategy do shape (`SHAPE_REGISTRY`, o mesmo
    registry em que `engine.pipeline.measure` despacha) em vez de un segundo
    dispatch por shape mantido à parte — um único lugar para atualizar quando
    um shape é adicionado, não dos."""

    strategy = SHAPE_REGISTRY.get(shape)
    if strategy is None:
        return None, None
    return strategy.pool_numerator_denominator(cast(dict[str, object], memoria))
