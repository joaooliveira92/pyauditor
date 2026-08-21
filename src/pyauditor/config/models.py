"""Pydantic models for `inms-<n>.yaml` indicator configs.

All 4 shapes from docs/spec/inms-pipeline.md §2/§3 are modeled: `ratio`
(ticket 02), `segmented_ratio` (ticket 04), `count_difference` (ticket 05),
`external_catalog_sum` (ticket 06).
"""
from __future__ import annotations

from typing import Annotated, Final, Literal, Self

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

from pyauditor.config._paths import reject_unsafe_relative_path

type _SafeRelativePath = Annotated[str, AfterValidator(reject_unsafe_relative_path)]

__all__: Final[tuple[str, ...]] = (
    "Calculation",
    "ColumnContains",
    "ColumnEquals",
    "ColumnIn",
    "CountDifferenceCalculation",
    "DurationAtMost",
    "ExternalCatalogSumCalculation",
    "Filter",
    "InSetCheck",
    "Indicator",
    "IndicatorConfig",
    "NotNullCheck",
    "Penalty",
    "PrecomputedTableCalculation",
    "QualityGateCheck",
    "QualityGates",
    "RatioCalculation",
    "Scope",
    "SegmentedCategory",
    "SegmentedRatioCalculation",
    "Source",
    "Target",
)

# ---------------------------------------------------------------------------
# Shared config — immutable, strict, forbid extra
# ---------------------------------------------------------------------------
_StrictFrozen: Final[ConfigDict] = ConfigDict(
    frozen=True,
    strict=True,
    extra="forbid",
    str_strip_whitespace=True,
)


class Indicator(BaseModel):
    model_config = _StrictFrozen
    id: str = Field(min_length=1)
    contractual_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    # Distinguishes measurements that share `contractual_id` (per-asset
    # indicators — spec §2.1 — measured independently per sistema/serviço,
    # e.g. INMS 1.14's File Server vs WI-FI). None for single-asset
    # indicators, where `contractual_id` alone already identifies the row.
    asset: str | None = Field(default=None, min_length=1)


class Scope(BaseModel):
    model_config = _StrictFrozen
    # Default contract é o do MinC — o loader injeta o contrato correto
    # por órgão quando o YAML vem de `configs/_shared/` (single-source).
    contract: str = Field(default="40/2022 - Ministério da Cultura", min_length=1)
    # "MTur" per docs/spreadsheet.md's MinC/MTur segregation — see
    # excel/report.py's consolidation step (spec §13).
    orgao: Literal["MinC", "MTur"] = "MinC"


class Source(BaseModel):
    model_config = _StrictFrozen
    dataset: str | None = Field(default=None, min_length=1)
    csv: _SafeRelativePath | None = Field(default=None, min_length=1)
    delimiter: str = Field(default=";", min_length=1)
    encoding: str = Field(default="utf-8-sig", min_length=1)
    id_column: str = Field(default="Nº Solicitacao", min_length=1)
    # Coluna de período do dataset (opcional no modelo — §2 da spec
    # competencia-cli-equipe). Obrigatoria na execucao: todo fluxo real passa
    # um PeriodoAfericao, e aí a ausência vira erro acionável (periodo.py).
    period_column: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _check_csv_or_dataset(self) -> Self:
        has_dataset = self.dataset is not None
        has_csv = self.csv is not None
        if has_dataset == has_csv:
            raise ValueError(
                "source must specify exactly one of 'dataset' or 'csv'"
            )
        return self


class NotNullCheck(BaseModel):
    model_config = _StrictFrozen
    type: Literal["not_null"]
    column: str = Field(min_length=1)


class InSetCheck(BaseModel):
    model_config = _StrictFrozen
    type: Literal["in_set"]
    column: str = Field(min_length=1)
    values: list[str] = Field(min_length=1)


type QualityGateCheck = Annotated[
    NotNullCheck | InSetCheck, Field(discriminator="type")
]


class QualityGates(BaseModel):
    model_config = _StrictFrozen
    checks: list[QualityGateCheck] = Field(default_factory=list)


class ColumnEquals(BaseModel):
    model_config = _StrictFrozen
    column: str = Field(min_length=1)
    equals: str


class ColumnNotEquals(BaseModel):
    model_config = _StrictFrozen
    column: str = Field(min_length=1)
    not_equals: str


class ColumnContains(BaseModel):
    model_config = _StrictFrozen
    column: str = Field(min_length=1)
    contains: str = Field(min_length=1)


class ColumnIn(BaseModel):
    model_config = _StrictFrozen
    column: str = Field(min_length=1)
    in_values: list[str] = Field(min_length=1)


class DurationAtMost(BaseModel):
    """Matches rows where an `H:MM:SS` (or `D:HH:MM:SS`) duration column is
    at most `max_seconds`."""

    model_config = _StrictFrozen
    column: str = Field(min_length=1)
    max_seconds: int = Field(ge=0)


# Smart union — members distinguished by distinct field names, no discriminator
type Filter = ColumnEquals | ColumnNotEquals | ColumnContains | ColumnIn | DurationAtMost


class RatioCalculation(BaseModel):
    model_config = _StrictFrozen
    shape: Literal["ratio"]
    aggregation: Literal["count_distinct", "sum", "precomputed"]
    numerator_filter: Filter | None = None
    denominator_filter: Filter | None = None
    sum_numerator_column: str | None = Field(default=None, min_length=1)
    # Mutually exclusive: `sum_denominator_extra_column` for ΣX/(ΣX+ΣY)
    # (denominator = numerator + extra); `sum_numerator_subtract_column` for
    # (ΣX-ΣY)/ΣX (denominator = the raw column sum, numerator = that minus
    # the subtracted column — e.g. INMS 1.6 (ΣCA-ΣCR)/ΣCA).
    sum_denominator_extra_column: str | None = Field(default=None, min_length=1)
    sum_numerator_subtract_column: str | None = Field(default=None, min_length=1)
    precomputed_result_column: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _check_fields_for_aggregation(self) -> Self:
        if self.aggregation == "count_distinct" and self.numerator_filter is None:
            raise ValueError("count_distinct requires numerator_filter")
        if self.aggregation == "sum":
            if self.sum_numerator_column is None:
                raise ValueError("sum requires sum_numerator_column")
            has_extra = self.sum_denominator_extra_column is not None
            has_subtract = self.sum_numerator_subtract_column is not None
            if has_extra == has_subtract:
                raise ValueError(
                    "sum requires exactly one of sum_denominator_extra_column, "
                    "sum_numerator_subtract_column"
                )
        if self.aggregation == "precomputed" and self.precomputed_result_column is None:
            raise ValueError("precomputed requires precomputed_result_column")
        return self


class SegmentedCategory(BaseModel):
    model_config = _StrictFrozen
    name: str = Field(min_length=1)
    denominator_filter: Filter
    numerator_filter: Filter
    step_points: float = Field(ge=0)


class SegmentedRatioCalculation(BaseModel):
    model_config = _StrictFrozen
    shape: Literal["segmented_ratio"]
    step_size_pct: float = Field(gt=0)
    categories: list[SegmentedCategory] = Field(min_length=1)


class CountDifferenceCalculation(BaseModel):
    model_config = _StrictFrozen
    shape: Literal["count_difference"]
    recommended_filter: Filter | None = None
    implemented_filter: Filter
    penalty_per_unit: float = Field(ge=0)


class ExternalCatalogSumCalculation(BaseModel):
    model_config = _StrictFrozen
    shape: Literal["external_catalog_sum"]
    occurrence_id_column: str = Field(min_length=1)
    catalog_codes_column: str = Field(min_length=1)
    catalog_codes_separator: str = Field(default=",", min_length=1)


class PrecomputedTableCalculation(BaseModel):
    model_config = _StrictFrozen
    shape: Literal["precomputed_table"]
    # Per-ativo result column (percentage, or a point total when
    # `result_is_percent` is false — e.g. INMS 1.8's PDT sum).
    result_column: str = Field(min_length=1)
    result_is_percent: bool = True
    # Optional per-ativo label for the ROM's breakdown table.
    name_column: str | None = Field(default=None, min_length=1)
    # Optional weighting columns for the headline pooled result (availability
    # is hours-weighted: sum(numerador)/sum(base) * 100).
    numerator_column: str | None = Field(default=None, min_length=1)
    denominator_column: str | None = Field(default=None, min_length=1)
    # Optional per-ativo penalty read straight from the dataset (the fiscal
    # apuração sheets already carry it). When absent, recomputed from target +
    # penalty (percent) or as points-excess over the target (points mode).
    penalty_column: str | None = Field(default=None, min_length=1)


type Calculation = Annotated[
    RatioCalculation
    | SegmentedRatioCalculation
    | CountDifferenceCalculation
    | ExternalCatalogSumCalculation
    | PrecomputedTableCalculation,
    Field(discriminator="shape"),
]


class Target(BaseModel):
    model_config = _StrictFrozen
    operator: Literal[">=", "<="]
    value: float = Field(ge=0, le=100)


class Penalty(BaseModel):
    model_config = _StrictFrozen
    base_points: float = Field(default=0.0, ge=0)
    step_points: float = Field(ge=0)
    step_size_pct: float = Field(gt=0)


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
    shape: Literal["ratio"]
    numerator: float = Field(ge=0)
    denominator: float = Field(ge=0)
    result_pct: float = Field(ge=0, le=100)
    conforms: bool
    penalty_points: float = Field(ge=0)


class SegmentedRatioAcceptanceExpected(BaseModel):
    model_config = _StrictFrozen
    shape: Literal["segmented_ratio"]
    result_pct: float = Field(ge=0, le=100)
    conforms: bool
    penalty_points: float = Field(ge=0)
    categories: list[AcceptanceTestCategoryExpected] = Field(min_length=1)


class CountDifferenceAcceptanceExpected(BaseModel):
    model_config = _StrictFrozen
    shape: Literal["count_difference"]
    result_pct: float = Field(ge=0, le=100)
    conforms: bool
    penalty_points: float = Field(ge=0)
    qrc: int = Field(ge=0)
    qcsi: int = Field(ge=0)
    cni: int


class ExternalCatalogSumAcceptanceExpected(BaseModel):
    model_config = _StrictFrozen
    shape: Literal["external_catalog_sum"]
    result_pct: float = Field(ge=0, le=100)
    conforms: bool
    penalty_points: float = Field(ge=0)
    total_points: int = Field(ge=0)
    occurrences: list[AcceptanceTestOccurrenceExpected] = Field(default_factory=list)


class PrecomputedTableAcceptanceExpected(BaseModel):
    model_config = _StrictFrozen
    shape: Literal["precomputed_table"]
    result_pct: float = Field(ge=0, le=100)
    conforms: bool
    penalty_points: float = Field(ge=0)


type AcceptanceTestExpected = Annotated[
    RatioAcceptanceExpected
    | SegmentedRatioAcceptanceExpected
    | CountDifferenceAcceptanceExpected
    | ExternalCatalogSumAcceptanceExpected
    | PrecomputedTableAcceptanceExpected,
    Field(discriminator="shape"),
]


class AcceptanceTest(BaseModel):
    model_config = _StrictFrozen
    expected: AcceptanceTestExpected


class IndicatorConfig(BaseModel):
    model_config = _StrictFrozen
    indicator: Indicator
    scope: Scope = Field(default_factory=Scope)
    source: Source
    quality_gates: QualityGates
    calculation: Calculation
    target: Target | None = None
    penalty: Penalty | None = None
    acceptance_test: AcceptanceTest | None = None

    @model_validator(mode="after")
    def _check_target_for_shape(self) -> Self:
        is_external = self.calculation.shape == "external_catalog_sum"
        if is_external and self.target is not None:
            raise ValueError("external_catalog_sum must not have target (Anexo E is point sum)")
        if not is_external and self.target is None:
            raise ValueError(f"{self.calculation.shape} requires target")
        if (
            self.calculation.shape == "precomputed_table"
            and self.calculation.result_is_percent
            and self.calculation.penalty_column is None
            and self.penalty is None
        ):
            raise ValueError(
                "precomputed_table (percent) requires penalty unless penalty_column is set"
            )
        return self