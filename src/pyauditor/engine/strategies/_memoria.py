"""Per-shape ``memoria`` TypedDicts: the shape-specific key→value bag each
strategy returns on its ``CalculationResult`` and that the ROM renderer, the
summary pooler, and the grouped-detail recompute read back. Tagging the shape
at the construction site replaces raw-literal key access (and the render-time
``_require_*`` guards) at each consumer.
"""

from typing import TypedDict


class RatioMemoria(TypedDict):
    numerator: float
    denominator: float


class CountDifferenceMemoria(TypedDict):
    QRC: int
    QCSI: int
    CNI: int


class SegmentedCategory(TypedDict):
    name: str
    numerator: int
    denominator: int
    result_pct: float
    penalty_points: float


class SegmentedRatioMemoria(TypedDict):
    categories: list[SegmentedCategory]


class CatalogOccurrence(TypedDict):
    occurrence_id: str
    catalog_id: str
    descricao: str
    pontos: int


class ExternalCatalogSumMemoria(TypedDict):
    occurrences: list[CatalogOccurrence]
    total_points: int


class PrecomputedCategory(TypedDict):
    name: str
    result_pct: float
    penalty_points: float


class PrecomputedTableMemoria(TypedDict):
    categories: list[PrecomputedCategory]


ShapeMemoria = (
    RatioMemoria
    | CountDifferenceMemoria
    | SegmentedRatioMemoria
    | ExternalCatalogSumMemoria
    | PrecomputedTableMemoria
)
