"""Snapshot esperado de resultado (acceptance test) — schema de *suporte a
teste*, não de entrada do pipeline: os fixtures `inms-*.yaml` carregam o
esperado para a suíte comparar com a medição (`matches acceptance test`).
Produção nunca consome os valores esperados em runtime (``acceptance_test``
é anulado por `cli/split.py` e `cli/measure.py`).

Extraído de `config/models.py` (ticket 02 SRP): é o único eixo do schema de
config com motivo de mudança independente (novos campos/ramos esperados,
divergência contratual por competência) e sem dependências internas — importa
apenas `pydantic`.
"""

from __future__ import annotations

from typing import Annotated, Final, Literal

from pydantic import BaseModel, ConfigDict, Field

__all__: Final[tuple[str, ...]] = (
    'AcceptanceTest',
    'AcceptanceTestCategoryExpected',
    'AcceptanceTestExpected',
    'AcceptanceTestOccurrenceExpected',
    'CountDifferenceAcceptanceExpected',
    'ExternalCatalogSumAcceptanceExpected',
    'PrecomputedTableAcceptanceExpected',
    'RatioAcceptanceExpected',
    'SegmentedRatioAcceptanceExpected',
)

_StrictFrozen: Final[ConfigDict] = ConfigDict(
    frozen=True,
    strict=True,
    extra='forbid',
    str_strip_whitespace=True,
)


class AcceptanceTestCategoryExpected(BaseModel):
    model_config = _StrictFrozen
    name: str
    numerator: int = Field(ge=0)
    denominator: int = Field(ge=0)
    result_pct: float = Field(ge=0, le=100)
    penalty_points: float = Field(ge=0)


class AcceptanceTestOccurrenceExpected(BaseModel):
    model_config = _StrictFrozen
    occurrence_id: str
    catalog_id: str
    pontos: int = Field(ge=0)


class RatioAcceptanceExpected(BaseModel):
    model_config = _StrictFrozen
    shape: Literal['ratio']
    numerator: float = Field(ge=0)
    denominator: float = Field(ge=0)
    result_pct: float = Field(ge=0, le=100)
    conforms: bool
    penalty_points: float = Field(ge=0)


class SegmentedRatioAcceptanceExpected(BaseModel):
    model_config = _StrictFrozen
    shape: Literal['segmented_ratio']
    result_pct: float = Field(ge=0, le=100)
    conforms: bool
    penalty_points: float = Field(ge=0)
    categories: list[AcceptanceTestCategoryExpected] = Field(min_length=1)


class CountDifferenceAcceptanceExpected(BaseModel):
    model_config = _StrictFrozen
    shape: Literal['count_difference']
    result_pct: float = Field(ge=0, le=100)
    conforms: bool
    penalty_points: float = Field(ge=0)
    qrc: int = Field(ge=0)
    qcsi: int = Field(ge=0)
    cni: int


class ExternalCatalogSumAcceptanceExpected(BaseModel):
    model_config = _StrictFrozen
    shape: Literal['external_catalog_sum']
    result_pct: float = Field(ge=0, le=100)
    conforms: bool
    penalty_points: float = Field(ge=0)
    total_points: int = Field(ge=0)
    occurrences: list[AcceptanceTestOccurrenceExpected] = Field(
        default_factory=list
    )


class PrecomputedTableAcceptanceExpected(BaseModel):
    model_config = _StrictFrozen
    shape: Literal['precomputed_table']
    result_pct: float = Field(ge=0, le=100)
    conforms: bool
    penalty_points: float = Field(ge=0)


type AcceptanceTestExpected = Annotated[
    RatioAcceptanceExpected
    | SegmentedRatioAcceptanceExpected
    | CountDifferenceAcceptanceExpected
    | ExternalCatalogSumAcceptanceExpected
    | PrecomputedTableAcceptanceExpected,
    Field(discriminator='shape'),
]


class AcceptanceTest(BaseModel):
    model_config = _StrictFrozen
    expected: AcceptanceTestExpected
