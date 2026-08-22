import pytest

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

CAPA: dict[str, object] = {"Número do contrato": "40/2022"}


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
        indicator_id=f"{contractual_id}-IND",
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
        "2026-06",
        minc,
        mtur,
        CAPA,
        valor_base=481534.80,
    )

    assert set(result.workbook.sheetnames) == {
        CAPA_SHEET,
        SERVICOS_SHEET,
        INMS_BASE_SHEET,
        GLOSAS_SHEET,
        CALCULO_SHEET,
    }
    assert result.workbook.sheetnames[0] == CAPA_SHEET


def test_inms_base_pools_minc_and_mtur_into_a_consolidado_row() -> None:
    minc = [_summary("INMS 1.1", orgao="MinC", numerator=90, denominator=100)]
    mtur = [_summary("INMS 1.1", orgao="MTur", numerator=10, denominator=100)]

    result = build_consolidated_workbook("2026-06", minc, mtur, {})

    sheet = result.workbook[INMS_BASE_SHEET]
    orgaos = [sheet.cell(row=r, column=7).value for r in range(2, sheet.max_row + 1)]
    assert set(orgaos) == {"Consolidado", "MinC", "MTur"}


def test_per_asset_indicators_never_get_a_consolidado_row() -> None:
    minc = [_summary("INMS 1.4", orgao="MinC")]
    mtur = [_summary("INMS 1.4", orgao="MTur")]

    result = build_consolidated_workbook("2026-06", minc, mtur, {})

    sheet = result.workbook[INMS_BASE_SHEET]
    orgaos = [sheet.cell(row=r, column=7).value for r in range(2, sheet.max_row + 1)]
    assert set(orgaos) == {"MinC", "MTur"}


def test_glosas_has_one_row_per_indicator_times_orgao_with_breaches() -> None:
    minc = [_summary("INMS 1.6", orgao="MinC", conforms=False, penalty_points=100.0)]
    mtur = [_summary("INMS 1.6", orgao="MTur", conforms=False, penalty_points=50.0)]

    result = build_consolidated_workbook("2026-06", minc, mtur, {}, valor_base=100000.0)

    sheet = result.workbook[GLOSAS_SHEET]
    rows = [
        (sheet.cell(row=r, column=5).value, sheet.cell(row=r, column=2).value) for r in range(2, 4)
    ]
    assert set(rows) == {("INMS 1.06", "MinC"), ("INMS 1.06", "MTur")}
    assert result.total_pontos == 150.0
    assert result.glosa_final == 100000.0 * 0.15 / 100


def test_glosa_capped_at_30_percent_of_aggregate() -> None:
    # Cap é por-órgão (issue 07): 20k pts = 20% por órgão, nenhum atinge 30% isolado,
    # então soma = 40% do valor base, não 30% do agregado.
    minc = [_summary("INMS 1.6", orgao="MinC", conforms=False, penalty_points=20000.0)]
    mtur = [_summary("INMS 1.6", orgao="MTur", conforms=False, penalty_points=20000.0)]

    result = build_consolidated_workbook("2026-06", minc, mtur, {}, valor_base=100000.0)

    assert result.glosa_final == 100000.0 * 20.0 / 100 + 100000.0 * 20.0 / 100


def test_capa_uses_valor_base_from_objetos() -> None:
    minc = [_summary("INMS 1.1")]
    mtur = [_summary("INMS 1.1", orgao="MTur")]

    result = build_consolidated_workbook("2026-06", minc, mtur, CAPA, valor_base=461063.58)

    sheet = result.workbook[CAPA_SHEET]
    campos = {
        sheet.cell(row=r, column=1).value: sheet.cell(row=r, column=2).value for r in range(4, 11)
    }
    assert campos["Valor mensal vigente"] == 461063.58
    assert campos["Valor global anual"] == 461063.58 * 12
    assert all("diverge" not in w for w in result.warnings)


def test_servicos_carries_item_values_by_index() -> None:
    minc = [_summary("INMS 1.1")]
    itens = (1.0, 2.0, 3.0)
    result = build_consolidated_workbook("2026-06", minc, [], {}, itens=itens)

    sheet = result.workbook[SERVICOS_SHEET]
    header = [cell.value for cell in sheet[1]]
    valor_col = header.index("Valor Mensal (R$)") + 1
    valores = {
        sheet.cell(row=r, column=1).value: sheet.cell(row=r, column=valor_col).value
        for r in range(2, 5)
    }
    assert valores == {1: 1.0, 2: 2.0, 3: 3.0}


def test_servicos_leaves_value_blank_when_itens_absent() -> None:
    result = build_consolidated_workbook("2026-06", [_summary("INMS 1.1")], [], {})

    sheet = result.workbook[SERVICOS_SHEET]
    header = [cell.value for cell in sheet[1]]
    valor_col = header.index("Valor Mensal (R$)") + 1
    assert sheet.cell(row=2, column=valor_col).value is None


def test_amnestied_decision_zeroes_pontos_and_is_preserved() -> None:
    minc = [_summary("INMS 1.6", orgao="MinC", conforms=False, penalty_points=100.0)]
    mtur: list[IndicatorSummary] = []
    decisao: dict[str, object] = {
        "Decisão Fiscal": "Aceita",
        "Justificativa": "fornecedor comprovou",
    }
    existing = {("INMS 1.06", "MinC"): decisao}

    result = build_consolidated_workbook(
        "2026-06",
        minc,
        mtur,
        {},
        existing_decisions=existing,
        valor_base=100000.0,
    )

    assert result.total_pontos == 0.0
    sheet = result.workbook[GLOSAS_SHEET]
    row = {
        sheet.cell(row=1, column=c).value: sheet.cell(row=2, column=c).value for c in range(1, 17)
    }
    assert row["Valor Glosa"] == 0.0
    assert row["Decisão Fiscal"] == "Aceita"
    assert row["Justificativa"] == "fornecedor comprovou"


def test_warns_when_a_decided_occurrence_disappears_on_rerun() -> None:
    minc = [_summary("INMS 1.6", orgao="MinC", conforms=True, penalty_points=0.0)]
    decisao: dict[str, object] = {"Decisão Fiscal": "Não aceita"}
    existing: dict[tuple[str, str], dict[str, object]] = {("INMS 1.6", "MinC"): decisao}

    result = build_consolidated_workbook("2026-06", minc, [], {}, existing_decisions=existing)

    assert any("não existe mais nesta rodada" in w for w in result.warnings)


def test_read_existing_decisions_returns_empty_for_missing_file(tmp_path) -> None:  # type: ignore[no-untyped-def]
    assert read_existing_decisions(tmp_path / "nope.xlsx") == {}


def test_read_existing_decisions_roundtrips_from_a_saved_workbook(tmp_path) -> None:  # type: ignore[no-untyped-def]
    minc = [_summary("INMS 1.6", orgao="MinC", conforms=False, penalty_points=100.0)]
    decisao: dict[str, object] = {"Decisão Fiscal": "Não aceita", "Observação do Gestor": "mantida"}
    result = build_consolidated_workbook(
        "2026-06",
        minc,
        [],
        {},
        existing_decisions={("INMS 1.06", "MinC"): decisao},
        valor_base=100000.0,
    )
    path = tmp_path / "relatorio_2026-06_consolidado.xlsx"
    result.workbook.save(path)

    decisions = read_existing_decisions(path)
    assert decisions[("INMS 1.06", "MinC")]["Decisão Fiscal"] == "Não aceita"
    assert decisions[("INMS 1.06", "MinC")]["Observação do Gestor"] == "mantida"


def test_glosas_summary_only_bolds_total_and_valor_glosa_rows() -> None:
    """Regression: a dead `bold` variable used to make every summary row
    (including "Fórmula"/"Limite"/"Percentual Aplicado") render bold."""
    minc = [_summary("INMS 1.6", orgao="MinC", conforms=False, penalty_points=100.0)]
    result = build_consolidated_workbook("2026-06", minc, [], {}, valor_base=100000.0)

    sheet = result.workbook[GLOSAS_SHEET]
    labels_bold = {
        sheet.cell(row=r, column=1).value: sheet.cell(row=r, column=1).font.bold
        for r in range(5, 10)
    }
    assert labels_bold["Total de Pontos"] is True
    assert labels_bold["Valor Glosa"] is True
    assert labels_bold["Fórmula (pontos x 0,001)"] is not True
    assert labels_bold["Limite"] is not True
    assert labels_bold["Percentual Aplicado"] is not True


def test_decision_columns_are_text_formatted_against_formula_injection() -> None:
    minc = [_summary("INMS 1.6", orgao="MinC", conforms=False, penalty_points=100.0)]
    decisao: dict[str, object] = {"Justificativa": "=cmd|' /C calc'!A1"}
    result = build_consolidated_workbook(
        "2026-06",
        minc,
        [],
        {},
        existing_decisions={("INMS 1.6", "MinC"): decisao},
        valor_base=100000.0,
    )

    sheet = result.workbook[GLOSAS_SHEET]
    header = [sheet.cell(row=1, column=c).value for c in range(1, 17)]
    justificativa_col = header.index("Justificativa") + 1
    assert sheet.cell(row=2, column=justificativa_col).number_format == "@"


def test_non_latin1_free_text_is_preserved_unmangled() -> None:
    """Regression: fiscal free text used to round-trip through cp1252,
    silently replacing any character outside that codepage with '?'."""
    minc = [_summary("INMS 1.6", orgao="MinC", conforms=False, penalty_points=100.0)]
    decisao: dict[str, object] = {"Observação do Gestor": "aprovado ✔ — café não é cafe’"}  # noqa: RUF001
    result = build_consolidated_workbook(
        "2026-06",
        minc,
        [],
        {},
        existing_decisions={("INMS 1.06", "MinC"): decisao},
        valor_base=100000.0,
    )

    sheet = result.workbook[GLOSAS_SHEET]
    header = [sheet.cell(row=1, column=c).value for c in range(1, 17)]
    col = header.index("Observação do Gestor") + 1
    assert sheet.cell(row=2, column=col).value == "aprovado ✔ — café não é cafe’"  # noqa: RUF001


def test_read_existing_decisions_rejects_duplicate_indicador_header(tmp_path) -> None:  # type: ignore[no-untyped-def]
    minc = [_summary("INMS 1.6", orgao="MinC", conforms=False, penalty_points=100.0)]
    result = build_consolidated_workbook("2026-06", minc, [], {}, valor_base=100000.0)
    sheet = result.workbook[GLOSAS_SHEET]
    sheet.cell(row=1, column=17, value="Indicador")  # hand-edited duplicate
    path = tmp_path / "relatorio_2026-06_consolidado.xlsx"
    result.workbook.save(path)

    with pytest.raises(ValueError, match="duplicada"):
        read_existing_decisions(path)
