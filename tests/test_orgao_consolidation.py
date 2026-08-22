"""MinC/MTur consolidation, per docs/spreadsheet.md's weighted formula.
No real MTur dataset exists yet — proven entirely with synthetic fixtures.
"""

from pyauditor.excel.orgao_consolidation import with_orgao_consolidation
from pyauditor.rom.summary import IndicatorSummary


def _summary(
    contractual_id: str,
    orgao: str,
    *,
    indicator_id: str | None = None,
    asset: str | None = None,
    shape: str = "ratio",
    numerator: float | None,
    denominator: float | None,
    target_operator: str | None = ">=",
    target_value: float | None = 98.0,
    penalty_points: float = 0.0,
) -> IndicatorSummary:
    return IndicatorSummary(
        indicator_id=indicator_id or f"{contractual_id}-IND",
        contractual_id=contractual_id,
        name=f"Indicador {contractual_id}",
        asset=asset,
        orgao=orgao,
        shape=shape,
        target_operator=target_operator,
        target_value=target_value,
        result_pct=(
            (numerator / denominator * 100) if numerator is not None and denominator else 0.0
        ),
        conforms=False,
        penalty_points=penalty_points,
        numerator=numerator,
        denominator=denominator,
        hard_failure=False,
    )


def test_consolidates_weighted_not_averaged() -> None:
    # MinC: 90/100 = 90%. MTur: 10/1000 = 1%. Simple average would be 45.5%;
    # the weighted formula must give (90+10)/(100+1000) = 9.09%.
    minc = _summary("INMS 1.1", "MinC", numerator=90, denominator=100)
    mtur = _summary("INMS 1.1", "MTur", numerator=10, denominator=1000)

    rows = with_orgao_consolidation([minc, mtur])

    assert len(rows) == 3  # MinC, MTur, + consolidated
    consolidated = next(r for r in rows if r.orgao == "Consolidado")
    assert consolidated.numerator == 100
    assert consolidated.denominator == 1100
    assert consolidated.result_pct == (100 / 1100) * 100
    assert consolidated.result_pct != (90.0 + 1.0) / 2  # not a simple average


def test_consolidated_conforms_matches_target() -> None:
    minc = _summary("INMS 1.1", "MinC", numerator=99, denominator=100, target_value=98.0)
    mtur = _summary("INMS 1.1", "MTur", numerator=99, denominator=100, target_value=98.0)

    rows = with_orgao_consolidation([minc, mtur])
    consolidated = next(r for r in rows if r.orgao == "Consolidado")

    assert consolidated.result_pct == 99.0
    assert consolidated.conforms is True


def test_consolidated_conforms_tolerates_float_rounding_at_the_target() -> None:
    # Pooled numerator (0.1 + 0.7 = 0.7999999999999999) and pooled
    # denominator (0.3 + 0.5 = 0.8) are mathematically equal but not
    # bit-identical IEEE-754 values, so the division lands a hair below
    # 100%. The same EPSILON tolerance engine/strategies/_target.py applies
    # per-órgão must also apply here, or a pooled result at the target could
    # be wrongly marked não conforme.
    minc = _summary("INMS 1.1", "MinC", numerator=0.1, denominator=0.3, target_value=100.0)
    mtur = _summary("INMS 1.1", "MTur", numerator=0.7, denominator=0.5, target_value=100.0)

    rows = with_orgao_consolidation([minc, mtur])
    consolidated = next(r for r in rows if r.orgao == "Consolidado")

    assert consolidated.result_pct < 100.0  # confirms the float-rounding premise
    assert consolidated.conforms is True


def test_consolidated_synthetic_row_carries_no_penalty_points() -> None:
    # A linha consolidada é apenas a visão analítica de INMS_BASE: os pontos
    # de glosa continuam somados por órgão (GLOSAS) — a linha sintética nunca
    # participa de cálculo financeiro para não contar duas vezes.
    minc = _summary("INMS 1.1", "MinC", numerator=50, denominator=100, penalty_points=300.0)
    mtur = _summary("INMS 1.1", "MTur", numerator=50, denominator=100, penalty_points=150.0)

    rows = with_orgao_consolidation([minc, mtur])
    consolidated = next(r for r in rows if r.orgao == "Consolidado")

    assert consolidated.penalty_points == 0.0


def test_per_asset_indicators_are_excluded() -> None:
    for contractual_id in ("INMS 1.4", "INMS 1.5", "INMS 1.14"):
        minc = _summary(contractual_id, "MinC", numerator=99.5, denominator=100)
        mtur = _summary(contractual_id, "MTur", numerator=99.5, denominator=100)

        rows = with_orgao_consolidation([minc, mtur])

        assert len(rows) == 2  # no synthetic consolidated row added
        assert {r.orgao for r in rows} == {"MinC", "MTur"}


def test_external_catalog_sum_is_not_consolidated() -> None:
    # No numerator/denominator to blend for a point sum (spec §11.2).
    minc = _summary(
        "INMS 1.8", "MinC", shape="external_catalog_sum", numerator=None, denominator=None
    )
    mtur = _summary(
        "INMS 1.8", "MTur", shape="external_catalog_sum", numerator=None, denominator=None
    )

    rows = with_orgao_consolidation([minc, mtur])

    assert len(rows) == 2


def test_single_orgao_is_left_untouched() -> None:
    minc = _summary("INMS 1.1", "MinC", numerator=90, denominator=100)

    rows = with_orgao_consolidation([minc])

    assert rows == [minc]


def test_consolidated_row_gets_a_distinct_indicator_id() -> None:
    minc = _summary("INMS 1.1", "MinC", indicator_id="INMS-1.1", numerator=90, denominator=100)
    mtur = _summary("INMS 1.1", "MTur", indicator_id="INMS-1.1", numerator=90, denominator=100)

    rows = with_orgao_consolidation([minc, mtur])

    ids = {r.indicator_id for r in rows}
    assert ids == {"INMS-1.1", "INMS-1.1-CONSOLIDADO"}


def test_multi_asset_pairs_are_consolidated_independently_per_asset() -> None:
    # Two assets of the same indicator, each with its own MinC/MTur pair.
    file_server_minc = _summary(
        "INMS 1.1", "MinC", asset="File Server", numerator=90, denominator=100
    )
    file_server_mtur = _summary(
        "INMS 1.1", "MTur", asset="File Server", numerator=10, denominator=100
    )
    wifi_minc = _summary("INMS 1.1", "MinC", asset="WI-FI", numerator=50, denominator=100)
    wifi_mtur = _summary("INMS 1.1", "MTur", asset="WI-FI", numerator=50, denominator=100)

    rows = with_orgao_consolidation([file_server_minc, file_server_mtur, wifi_minc, wifi_mtur])

    consolidated = [r for r in rows if r.orgao == "Consolidado"]
    assert len(consolidated) == 2
    by_asset = {r.asset: r for r in consolidated}
    assert by_asset["File Server"].numerator == 100
    assert by_asset["WI-FI"].numerator == 100
