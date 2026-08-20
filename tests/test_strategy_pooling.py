"""`pool_numerator_denominator` — each strategy answers its own pooling
question (ticket "production-readiness review", punch-list item 21) — used
by `rom/summary.py::summarize()` via `SHAPE_REGISTRY`."""

from pyauditor.engine.strategies import SHAPE_REGISTRY
from pyauditor.engine.strategies.count_difference import CountDifferenceStrategy
from pyauditor.engine.strategies.external_catalog_sum import ExternalCatalogSumStrategy
from pyauditor.engine.strategies.precomputed_table import PrecomputedTableStrategy
from pyauditor.engine.strategies.ratio import RatioStrategy
from pyauditor.engine.strategies.segmented_ratio import SegmentedRatioStrategy


def test_ratio_pools_numerator_and_denominator_directly() -> None:
    numerator, denominator = RatioStrategy().pool_numerator_denominator(
        {"numerator": 171, "denominator": 175}
    )
    assert numerator == 171.0
    assert denominator == 175.0


def test_segmented_ratio_pools_by_summing_categories() -> None:
    memoria: dict[str, object] = {
        "categories": [
            {"name": "Alta", "numerator": 10, "denominator": 20},
            {"name": "Baixa", "numerator": 5, "denominator": 10},
        ]
    }
    numerator, denominator = SegmentedRatioStrategy().pool_numerator_denominator(memoria)
    assert numerator == 15.0
    assert denominator == 30.0


def test_segmented_ratio_pooling_tolerates_malformed_categories() -> None:
    assert SegmentedRatioStrategy().pool_numerator_denominator({"categories": "not-a-list"}) == (
        None,
        None,
    )


def test_count_difference_pools_qcsi_as_numerator_and_qrc_as_denominator() -> None:
    numerator, denominator = CountDifferenceStrategy().pool_numerator_denominator(
        {"QRC": 10, "QCSI": 8, "CNI": 2}
    )
    assert numerator == 8.0
    assert denominator == 10.0


def test_external_catalog_sum_has_no_pooled_numerator_denominator() -> None:
    assert ExternalCatalogSumStrategy().pool_numerator_denominator({"total_points": 5}) == (
        None,
        None,
    )


def test_precomputed_table_has_no_pooled_numerator_denominator() -> None:
    assert PrecomputedTableStrategy().pool_numerator_denominator({"categories": []}) == (
        None,
        None,
    )


def test_shape_registry_covers_every_shape_with_a_pooling_strategy() -> None:
    for strategy in SHAPE_REGISTRY.values():
        result = strategy.pool_numerator_denominator({})
        assert isinstance(result, tuple)
        assert len(result) == 2
