from pyauditor.excel.consolidate import (
    CALCULO_SHEET,
    CAPA_SHEET,
    GLOSAS_SHEET,
    INMS_BASE_SHEET,
    SERVICOS_SHEET,
    build_consolidated_workbook,
    read_existing_decisions,
)
from pyauditor.rom.summary import IndicatorSummary


def _summary(
    contractual_id: str,
    *,
    orgao: str = "MinC",
    shape: str = "ratio",
    result_pct: float = 97.5,
    conforms: bool = True,
    penalty_points: float = 0.0,
    numerator: float | None = 171,
    denominator: float | None = 175,
    target_operator: str | None = ">=",
    target_value: float | None = 98.0,
) -> IndicatorSummary:
    return IndicatorSummary(
        indicator_id=f"{contractual_id}-{orgao}",
        contractual_id=contractual_id,
        name=f"Indicador {contractual_id}",
        asset=None,
        orgao=orgao,
        shape=shape,
        target_operator=target_operator,
        target_value=target_value,
        result_pct=result_pct,
        conforms=conforms,
        penalty_points=penalty_points,
        numerator=numerator,
        denominator=denominator,
        hard_failure=False,
    )


def test_builds_all_five_financial_sheets() -> None:
    minc = [_summary("INMS 1.1", orgao="MinC")]
    mtur = [_summary("INMS 1.1", orgao="MTur")]

    result = build_consolidated_workbook(
        "2026-06", minc, mtur,
        {"Valor mensal vigente": 481534.80}, {"Valor mensal vigente": 481534.80},
    )

    assert set(result.workbook.sheetnames) == {
        CAPA_SHEET, SERVICOS_SHEET, INMS_BASE_SHEET, GLOSAS_SHEET, CALCULO_SHEET,
    }
    assert result.workbook.sheetnames[0] == CAPA_SHEET


def test_inms_base_pools_minc_and_mtur_into_a_consolidado_row() -> None:
    minc = [_summary("INMS 1.1", orgao="MinC", numerator=90, denominator=100)]
    mtur = [_summary("INMS 1.1", orgao="MTur", numerator=10, denominator=100)]

    result = build_consolidated_workbook("2026-06", minc, mtur, {}, {})

    sheet = result.workbook[INMS_BASE_SHEET]
    orgaos = [sheet.cell(row=r, column=7).value for r in range(2, sheet.max_row + 1)]
    assert set(orgaos) == {"Consolidado", "MinC", "MTur"}


def test_per_asset_indicators_never_get_a_consolidado_row() -> None:
    minc = [_summary("INMS 1.4", orgao="MinC")]
    mtur = [_summary("INMS 1.4", orgao="MTur")]

    result = build_consolidated_workbook("2026-06", minc, mtur, {}, {})

    sheet = result.workbook[INMS_BASE_SHEET]
    orgaos = [sheet.cell(row=r, column=7).value for r in range(2, sheet.max_row + 1)]
    assert set(orgaos) == {"MinC", "MTur"}


def test_glosas_has_one_row_per_indicator_times_orgao_with_breaches() -> None:
    minc = [_summary("INMS 1.6", orgao="MinC", conforms=False, penalty_points=100.0)]
    mtur = [_summary("INMS 1.6", orgao="MTur", conforms=False, penalty_points=50.0)]

    valores: dict[str, object] = {"Valor mensal vigente": 100000.0}
    result = build_consolidated_workbook("2026-06", minc, mtur, valores, valores)

    sheet = result.workbook[GLOSAS_SHEET]
    rows = [
        (sheet.cell(row=r, column=5).value, sheet.cell(row=r, column=2).value)
        for r in range(2, 4)
    ]
    assert set(rows) == {("INMS 1.6", "MinC"), ("INMS 1.6", "MTur")}
    assert result.total_pontos == 150.0
    assert result.glosa_final == 100000.0 * 0.15 / 100


def test_glosa_capped_at_30_percent_of_aggregate() -> None:
    minc = [_summary("INMS 1.6", orgao="MinC", conforms=False, penalty_points=20000.0)]
    mtur = [_summary("INMS 1.6", orgao="MTur", conforms=False, penalty_points=20000.0)]

    valores: dict[str, object] = {"Valor mensal vigente": 100000.0}
    result = build_consolidated_workbook("2026-06", minc, mtur, valores, valores)

    assert result.glosa_final == 100000.0 * 30.0 / 100


def test_capa_uses_minc_valor_and_warns_on_divergence() -> None:
    minc = [_summary("INMS 1.1")]
    mtur = [_summary("INMS 1.1", orgao="MTur")]

    result = build_consolidated_workbook(
        "2026-06", minc, mtur,
        {"Valor mensal vigente": 100000.0}, {"Valor mensal vigente": 999.0},
    )

    sheet = result.workbook[CAPA_SHEET]
    campos = {
        sheet.cell(row=r, column=1).value: sheet.cell(row=r, column=2).value
        for r in range(4, 11)
    }
    assert campos["Valor mensal vigente"] == 100000.0
    assert any("diverge" in w for w in result.warnings)


def test_amnestied_decision_zeroes_pontos_and_is_preserved() -> None:
    minc = [_summary("INMS 1.6", orgao="MinC", conforms=False, penalty_points=100.0)]
    mtur: list[IndicatorSummary] = []
    decisao: dict[str, object] = {
        "Decisão Fiscal": "Aceita", "Justificativa": "fornecedor comprovou",
    }
    existing = {("INMS 1.6", "MinC"): decisao}

    result = build_consolidated_workbook(
        "2026-06", minc, mtur, {"Valor mensal vigente": 100000.0}, {},
        existing_decisions=existing,
    )

    assert result.total_pontos == 0.0
    sheet = result.workbook[GLOSAS_SHEET]
    row = {
        sheet.cell(row=1, column=c).value: sheet.cell(row=2, column=c).value
        for c in range(1, 17)
    }
    assert row["Valor Glosa"] == 0.0
    assert row["Decisão Fiscal"] == "Aceita"
    assert row["Justificativa"] == "fornecedor comprovou"


def test_warns_when_a_decided_occurrence_disappears_on_rerun() -> None:
    minc = [_summary("INMS 1.6", orgao="MinC", conforms=True, penalty_points=0.0)]
    decisao: dict[str, object] = {"Decisão Fiscal": "Não aceita"}
    existing: dict[tuple[str, str], dict[str, object]] = {("INMS 1.6", "MinC"): decisao}

    result = build_consolidated_workbook("2026-06", minc, [], {}, {}, existing_decisions=existing)

    assert any("não existe mais nesta rodada" in w for w in result.warnings)


def test_read_existing_decisions_returns_empty_for_missing_file(tmp_path) -> None:  # type: ignore[no-untyped-def]
    assert read_existing_decisions(tmp_path / "nope.xlsx") == {}


def test_read_existing_decisions_roundtrips_from_a_saved_workbook(tmp_path) -> None:  # type: ignore[no-untyped-def]
    minc = [_summary("INMS 1.6", orgao="MinC", conforms=False, penalty_points=100.0)]
    decisao: dict[str, object] = {"Decisão Fiscal": "Não aceita", "Observação do Gestor": "mantida"}
    result = build_consolidated_workbook(
        "2026-06", minc, [], {"Valor mensal vigente": 100000.0}, {},
        existing_decisions={("INMS 1.6", "MinC"): decisao},
    )
    path = tmp_path / "relatorio_2026-06_consolidado.xlsx"
    result.workbook.save(path)

    decisions = read_existing_decisions(path)
    assert decisions[("INMS 1.6", "MinC")]["Decisão Fiscal"] == "Não aceita"
    assert decisions[("INMS 1.6", "MinC")]["Observação do Gestor"] == "mantida"
