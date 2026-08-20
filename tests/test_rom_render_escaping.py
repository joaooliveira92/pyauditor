"""A stray `|`/newline in CSV-derived data must not corrupt the ROM's
Markdown tables — ticket "ROM package review", finding 1."""

from pyauditor.engine.strategies.base import CalculationResult
from pyauditor.rom.render import (
    render_external_catalog_sum_memoria,
    render_precomputed_table_memoria,
    render_segmented_ratio_memoria,
)


def test_segmented_ratio_escapes_pipe_in_category_name() -> None:
    calculation = CalculationResult(
        result_pct=90.0,
        conforms=True,
        penalty_points=0.0,
        memoria={
            "categories": [
                {
                    "name": "Alta | maliciosa",
                    "numerator": 1,
                    "denominator": 1,
                    "result_pct": 100.0,
                    "penalty_points": 0.0,
                }
            ]
        },
    )

    markdown = render_segmented_ratio_memoria(calculation)

    assert "Alta \\| maliciosa" in markdown
    # The escaped row must still be exactly one table row (one line).
    assert "Alta | maliciosa" not in markdown.replace("Alta \\| maliciosa", "")


def test_external_catalog_sum_escapes_pipe_and_newline_in_descricao() -> None:
    calculation = CalculationResult(
        result_pct=0.0,
        conforms=True,
        penalty_points=5.0,
        memoria={
            "occurrences": [
                {
                    "occurrence_id": "OC-1",
                    "catalog_id": "E-001",
                    "descricao": "linha 1\nlinha 2 | forjada",
                    "pontos": 5,
                }
            ],
            "total_points": 5,
        },
    )

    markdown = render_external_catalog_sum_memoria(calculation)

    assert "\n" not in markdown.split("| OC-1 |", 1)[1].split("\n", 1)[0]
    assert "\\|" in markdown


def test_precomputed_table_escapes_pipe_in_asset_name() -> None:
    calculation = CalculationResult(
        result_pct=0.0,
        conforms=True,
        penalty_points=0.0,
        memoria={
            "categories": [
                {"name": "WI-FI | forjado", "result_pct": 99.0, "penalty_points": 0.0}
            ]
        },
    )

    markdown = render_precomputed_table_memoria(calculation)

    assert "WI-FI \\| forjado" in markdown
