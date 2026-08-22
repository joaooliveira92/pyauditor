"""Module-level registry of calculation strategies, keyed by `shape`
(spec §9)."""

from pyauditor.engine.strategies.base import CalculationStrategy
from pyauditor.engine.strategies.count_difference import CountDifferenceStrategy
from pyauditor.engine.strategies.external_catalog_sum import (
    ExternalCatalogSumStrategy,
)
from pyauditor.engine.strategies.precomputed_table import (
    PrecomputedTableStrategy,
)
from pyauditor.engine.strategies.ratio import RatioStrategy
from pyauditor.engine.strategies.segmented_ratio import SegmentedRatioStrategy

SHAPE_REGISTRY: dict[str, CalculationStrategy] = {
    'ratio': RatioStrategy(),
    'segmented_ratio': SegmentedRatioStrategy(),
    'count_difference': CountDifferenceStrategy(),
    'external_catalog_sum': ExternalCatalogSumStrategy(),
    'precomputed_table': PrecomputedTableStrategy(),
}
