from pyauditor.excel.groups import GROUP_TABS, primary_group
from pyauditor.excel.report import (
    CADASTROS_SHEET,
    EVIDENCIAS_SHEET,
    GLOSAS_SHEET,
    INMS_BASE_SHEET,
    build_report_workbook,
)
from pyauditor.rom.summary import IndicatorSummary


def _summary(
    indicator_id: str,
    contractual_id: str,
    *,
    asset: str | None = None,
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
        indicator_id=indicator_id,
        contractual_id=contractual_id,
        name=f"Indicador {contractual_id}",
        asset=asset,
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


def test_primary_group_picks_first_listed_tab() -> None:
    assert primary_group("INMS 1.4") == "MONITORAMENTO_NOC_SOC"
    assert primary_group("INMS 1.1") == "ATENDIMENTO_N1"  # listed in N1, N2, N3 -> N1 wins
    assert primary_group("INMS 1.10") == "OPERACAO_N3"  # only in N3


def test_primary_group_none_for_indicator_outside_group_tabs() -> None:
    assert primary_group("INMS 1.8") is None  # external_catalog_sum isn't on any group tab


def test_build_report_workbook_has_inms_base_and_all_group_tabs() -> None:
    summaries = [_summary("INMS-1.1", "INMS 1.1"), _summary("INMS-1.4", "INMS 1.4")]

    workbook = build_report_workbook("2026-06", summaries)

    assert INMS_BASE_SHEET in workbook.sheetnames
    for group in GROUP_TABS:
        assert group in workbook.sheetnames


def test_inms_base_row_matches_summary_and_leaves_fiscal_columns_blank() -> None:
    summaries = [
        _summary("INMS-1.1", "INMS 1.1", result_pct=97.71, conforms=False, penalty_points=222.14)
    ]

    workbook = build_report_workbook("2026-06", summaries)
    sheet = workbook[INMS_BASE_SHEET]

    header = [cell.value for cell in sheet[1]]
    row = {header[i]: sheet.cell(row=2, column=i + 1).value for i in range(len(header))}

    assert row["Competência"] == "2026-06"
    assert row["Código INMS"] == "INMS 1.01"
    assert row["Grupo operacional"] == "ATENDIMENTO_N1"
    assert row["Numerador"] == 171
    assert row["Denominador"] == 175
    assert row["Resultado calculado"] == 97.71
    assert row["Conformidade"] == "Não conforme"
    assert row["Diferença para a meta"] == 0.29  # 98.0 - 97.71
    # fiscal-manual-only columns must stay blank, not fabricated
    assert row["Item contratual"] is None
    assert row["Justificativa"] is None
    assert row["Percentual de glosa"] is None


def test_inms_base_uses_shared_rule_for_max_target_direction() -> None:
    """Ticket 08 — o `report` e o `consolidate` derivam a linha `INMS_BASE` da
    mesma regra única: a "Diferença para a meta" respeita o sentido do operador
    (meta máxima `<=` ⇒ `result - target`), não `target - result` cego."""
    summaries = [
        _summary(
            "INMS-1.1",
            "INMS 1.1",
            result_pct=2.5,
            target_operator="<=",
            target_value=2.0,
            conforms=False,
        )
    ]

    workbook = build_report_workbook("2026-06", summaries)
    sheet = workbook[INMS_BASE_SHEET]

    header = [cell.value for cell in sheet[1]]
    row = {header[i]: sheet.cell(row=2, column=i + 1).value for i in range(len(header))}
    assert row["Diferença para a meta"] == 0.5  # 2.5 - 2.0, sentido invertido


def test_group_tabs_only_contain_their_indicators() -> None:
    summaries = [_summary("INMS-1.1", "INMS 1.1"), _summary("INMS-1.4", "INMS 1.4")]

    workbook = build_report_workbook("2026-06", summaries)

    n1_sheet = workbook["ATENDIMENTO_N1"]
    n1_codes = [n1_sheet.cell(row=r, column=1).value for r in range(2, n1_sheet.max_row + 1)]
    assert "INMS 1.01" in n1_codes
    assert "INMS 1.04" not in n1_codes

    noc_soc_sheet = workbook["MONITORAMENTO_NOC_SOC"]
    noc_soc_codes = [
        noc_soc_sheet.cell(row=r, column=1).value for r in range(2, noc_soc_sheet.max_row + 1)
    ]
    assert "INMS 1.04" in noc_soc_codes


def test_split_derived_summary_lands_on_its_own_categoria_tab() -> None:
    # `split` (spec §14) produces one measurement per Categoria — a derived
    # summary must land on the tab its own categoria names, not on
    # `primary_group`'s static first-listed tab for the contractual id.
    summaries = [
        _summary("INMS-01.OPERACAO_N3", "INMS 1.1"),
        _summary("INMS-01.ATENDIMENTO_N2", "INMS 1.1"),
    ]

    workbook = build_report_workbook("2026-06", summaries)

    n3_codes = [
        workbook["OPERACAO_N3"].cell(row=r, column=1).value
        for r in range(2, workbook["OPERACAO_N3"].max_row + 1)
    ]
    n2_codes = [
        workbook["ATENDIMENTO_N2"].cell(row=r, column=1).value
        for r in range(2, workbook["ATENDIMENTO_N2"].max_row + 1)
    ]
    n1_codes = [
        workbook["ATENDIMENTO_N1"].cell(row=r, column=1).value
        for r in range(2, workbook["ATENDIMENTO_N1"].max_row + 1)
    ]
    assert "INMS 1.01" in n3_codes
    assert "INMS 1.01" in n2_codes
    assert "INMS 1.01" not in n1_codes  # would be primary_group's first-listed tab

    base_sheet = workbook[INMS_BASE_SHEET]
    grupos = {
        str(base_sheet.cell(row=r, column=4).value)
        for r in range(2, base_sheet.max_row + 1)
    }
    assert grupos == {"OPERACAO_N3", "ATENDIMENTO_N2"}


def test_indicator_outside_group_tabs_only_appears_in_inms_base() -> None:
    summaries = [
        _summary(
            "INMS-1.8",
            "INMS 1.8",
            shape="external_catalog_sum",
            numerator=None,
            denominator=None,
            target_operator=None,
            target_value=None,
        )
    ]

    workbook = build_report_workbook("2026-06", summaries)

    base_sheet = workbook[INMS_BASE_SHEET]
    assert base_sheet.cell(row=2, column=5).value == "INMS 1.08"  # Código INMS column

    for group in GROUP_TABS:
        sheet = workbook[group]
        codes = [sheet.cell(row=r, column=1).value for r in range(2, sheet.max_row + 1)]
        assert "INMS 1.08" not in codes


def test_rows_sorted_by_contractual_id() -> None:
    summaries = [_summary("INMS-1.13", "INMS 1.13"), _summary("INMS-1.11", "INMS 1.11")]

    workbook = build_report_workbook("2026-06", summaries)
    sheet = workbook["ATENDIMENTO_N1"]

    codes = [str(sheet.cell(row=r, column=1).value) for r in range(2, sheet.max_row + 1)]
    assert codes == sorted(codes)


def test_rows_sorted_numerically_not_lexicographically() -> None:
    # "INMS 1.2" must sort before "INMS 1.10" — plain string comparison on
    # the minor version gets this backwards (lexicographic: "1.10" < "1.2").
    summaries = [
        _summary("INMS-1.1", "INMS 1.1"),
        _summary("INMS-1.2", "INMS 1.2"),
        _summary("INMS-1.7", "INMS 1.7"),
        _summary("INMS-1.11", "INMS 1.11"),
        _summary("INMS-1.12", "INMS 1.12"),
        _summary("INMS-1.13", "INMS 1.13"),
    ]

    workbook = build_report_workbook("2026-06", summaries)
    sheet = workbook[INMS_BASE_SHEET]

    codes = [sheet.cell(row=r, column=5).value for r in range(2, sheet.max_row + 1)]
    assert codes == [
        "INMS 1.01",
        "INMS 1.02",
        "INMS 1.07",
        "INMS 1.11",
        "INMS 1.12",
        "INMS 1.13",
    ]


def test_glosas_sheet_sums_penalty_points_across_all_indicators() -> None:
    summaries = [
        _summary("INMS-1.1", "INMS 1.1", penalty_points=222.14),
        _summary("INMS-1.11", "INMS 1.11", penalty_points=695.12),
    ]

    workbook = build_report_workbook("2026-06", summaries, valor_base=100_000.0)
    sheet = workbook[GLOSAS_SHEET]

    header = [cell.value for cell in sheet[1]]
    row = {header[i]: sheet.cell(row=2, column=i + 1).value for i in range(len(header))}

    assert row["Competência"] == "2026-06"
    assert row["Σ Pontos_NMS do mês"] == 917.26  # 222.14 + 695.12
    assert row["Percentual de ajuste"] == 0.91726  # 917.26 * 0.001
    assert row["Valor-base"] == 100_000.0
    assert row["Valor da glosa"] == 917.26  # 0.91726% de 100.000
    assert row["Teto atingido?"] == "N"
    assert row["Saldo rolado para o mês seguinte (p.p.)"] is None


def test_glosas_sheet_caps_at_30_percent_and_reports_rollover() -> None:
    # 40000 pontos -> 40% bruto, capado em 30%, 10 p.p. de excedente
    summaries = [
        _summary("INMS-1.8", "INMS 1.8", shape="external_catalog_sum", penalty_points=40_000.0)
    ]

    workbook = build_report_workbook("2026-06", summaries, valor_base=100_000.0)
    sheet = workbook[GLOSAS_SHEET]

    header = [cell.value for cell in sheet[1]]
    row = {header[i]: sheet.cell(row=2, column=i + 1).value for i in range(len(header))}

    assert row["Percentual de ajuste"] == 30.0
    assert row["Valor da glosa"] == 30_000.0
    assert row["Teto atingido?"] == "S"
    assert row["Saldo rolado para o mês seguinte (p.p.)"] == 10.0


def test_glosas_sheet_without_valor_base_leaves_valor_da_glosa_blank() -> None:
    summaries = [_summary("INMS-1.1", "INMS 1.1", penalty_points=222.14)]

    workbook = build_report_workbook("2026-06", summaries)  # valor_base defaults to None
    sheet = workbook[GLOSAS_SHEET]

    header = [cell.value for cell in sheet[1]]
    row = {header[i]: sheet.cell(row=2, column=i + 1).value for i in range(len(header))}

    assert row["Valor-base"] is None
    assert row["Valor da glosa"] is None
    assert row["Percentual de ajuste"] == 0.22214


def test_inms_base_never_synthesizes_a_consolidado_row() -> None:
    # `report` is per-órgão by construction (ticket 02, multi-org-pipeline
    # map) — pooling MinC+MTur lives in `consolidate` (excel/consolidate.py),
    # not here, even if a caller passes mixed-órgão summaries directly.
    minc = _summary(
        "INMS-1.1-MINC",
        "INMS 1.1",
        orgao="MinC",
        numerator=90,
        denominator=100,
        penalty_points=100.0,
    )
    mtur = _summary(
        "INMS-1.1-MTUR",
        "INMS 1.1",
        orgao="MTur",
        numerator=10,
        denominator=100,
        penalty_points=50.0,
    )

    workbook = build_report_workbook("2026-06", [minc, mtur])

    base_sheet = workbook[INMS_BASE_SHEET]
    orgaos_in_base = [
        str(base_sheet.cell(row=r, column=7).value) for r in range(2, base_sheet.max_row + 1)
    ]
    assert set(orgaos_in_base) == {"MinC", "MTur"}

    glosas_sheet = workbook[GLOSAS_SHEET]
    header = [cell.value for cell in glosas_sheet[1]]
    row = {header[i]: glosas_sheet.cell(row=2, column=i + 1).value for i in range(len(header))}
    assert row["Σ Pontos_NMS do mês"] == 150.0


def test_cadastros_sheet_populated_from_configs() -> None:
    from pyauditor.config.models import (
        ColumnEquals,
        ExternalCatalogSumCalculation,
        Indicator,
        IndicatorConfig,
        Penalty,
        QualityGates,
        RatioCalculation,
        Scope,
        Source,
        Target,
    )

    configs = [
        IndicatorConfig(
            indicator=Indicator(
                id="INMS-1.1",
                contractual_id="INMS 1.1",
                name="Incidentes atendidos dentro do prazo",
            ),
            scope=Scope(contract="40/2022"),
            source=Source(csv="inms-001-01.csv"),
            quality_gates=QualityGates(),
            calculation=RatioCalculation(
                shape="ratio",
                aggregation="count_distinct",
                numerator_filter=ColumnEquals(column="No prazo", equals="S"),
            ),
            target=Target(operator=">=", value=98.0),
            penalty=Penalty(base_points=165, step_points=20, step_size_pct=0.1),
        ),
        IndicatorConfig(
            indicator=Indicator(
                id="INMS-1.8",
                contractual_id="INMS 1.8",
                name="Ocorrências de Desconformidade Técnica",
            ),
            scope=Scope(contract="40/2022"),
            source=Source(csv="inms-001-08.csv"),
            quality_gates=QualityGates(),
            calculation=ExternalCatalogSumCalculation(
                shape="external_catalog_sum",
                occurrence_id_column="ID_Ocorrencia",
                catalog_codes_column="Codigos_Anexo_E",
            ),
        ),
    ]

    summaries = [_summary("INMS-1.1", "INMS 1.1")]
    workbook = build_report_workbook("2026-06", summaries, configs=configs)

    assert CADASTROS_SHEET in workbook.sheetnames
    sheet = workbook[CADASTROS_SHEET]

    header = [cell.value for cell in sheet[1]]
    assert "Código INMS" in header
    assert "Descrição" in header
    assert "Formato" in header
    assert "Meta" in header
    assert "Sentido" in header

    codes = [sheet.cell(row=r, column=1).value for r in range(2, sheet.max_row + 1)]
    assert "INMS 1.01" in codes
    assert "INMS 1.08" in codes


def test_cadastros_sheet_skipped_when_no_configs() -> None:
    summaries = [_summary("INMS-1.1", "INMS 1.1")]
    workbook = build_report_workbook("2026-06", summaries)

    assert CADASTROS_SHEET not in workbook.sheetnames


def test_evidencias_sheet_populated_from_configs() -> None:
    from pyauditor.config.models import (
        ColumnEquals,
        ExternalCatalogSumCalculation,
        Indicator,
        IndicatorConfig,
        Penalty,
        QualityGates,
        RatioCalculation,
        Scope,
        Source,
        Target,
    )

    configs = [
        IndicatorConfig(
            indicator=Indicator(
                id="INMS-1.1",
                contractual_id="INMS 1.1",
                name="Incidentes atendidos dentro do prazo",
            ),
            scope=Scope(contract="40/2022"),
            source=Source(csv="inms-001-01.csv"),
            quality_gates=QualityGates(),
            calculation=RatioCalculation(
                shape="ratio",
                aggregation="count_distinct",
                numerator_filter=ColumnEquals(column="No prazo", equals="S"),
            ),
            target=Target(operator=">=", value=98.0),
            penalty=Penalty(base_points=165, step_points=20, step_size_pct=0.1),
        ),
        IndicatorConfig(
            indicator=Indicator(
                id="INMS-1.8",
                contractual_id="INMS 1.8",
                name="Ocorrências de Desconformidade Técnica",
            ),
            scope=Scope(contract="40/2022"),
            source=Source(csv="inms-001-08.csv"),
            quality_gates=QualityGates(),
            calculation=ExternalCatalogSumCalculation(
                shape="external_catalog_sum",
                occurrence_id_column="ID_Ocorrencia",
                catalog_codes_column="Codigos_Anexo_E",
            ),
        ),
    ]

    summaries = [_summary("INMS-1.1", "INMS 1.1")]
    workbook = build_report_workbook("2026-06", summaries, configs=configs)

    assert EVIDENCIAS_SHEET in workbook.sheetnames
    sheet = workbook[EVIDENCIAS_SHEET]

    header = [cell.value for cell in sheet[1]]
    assert "Competência" in header
    assert "Código INMS" in header
    assert "Tipo de evidência" in header
    assert "Descrição" in header
    assert "Fonte/URL" in header
    assert "Responsável pela coleta" in header
    assert "Data de coleta" in header
    assert "Status" in header

    codes = [sheet.cell(row=r, column=2).value for r in range(2, sheet.max_row + 1)]
    assert "INMS 1.01" in codes
    assert "INMS 1.08" in codes

    for row_idx in range(2, sheet.max_row + 1):
        assert sheet.cell(row=row_idx, column=1).value == "2026-06"
        assert sheet.cell(row=row_idx, column=8).value == "Pendente"


def test_evidencias_sheet_has_dropdown_validations() -> None:
    from pyauditor.config.models import (
        ColumnEquals,
        Indicator,
        IndicatorConfig,
        Penalty,
        QualityGates,
        RatioCalculation,
        Scope,
        Source,
        Target,
    )

    configs = [
        IndicatorConfig(
            indicator=Indicator(id="INMS-1.1", contractual_id="INMS 1.1", name="Teste"),
            scope=Scope(contract="40/2022"),
            source=Source(csv="test.csv"),
            quality_gates=QualityGates(),
            calculation=RatioCalculation(
                shape="ratio",
                aggregation="count_distinct",
                numerator_filter=ColumnEquals(column="X", equals="S"),
            ),
            target=Target(operator=">=", value=98.0),
            penalty=Penalty(base_points=0, step_points=20, step_size_pct=0.1),
        ),
    ]

    workbook = build_report_workbook("2026-06", [_summary("INMS-1.1", "INMS 1.1")], configs=configs)
    sheet = workbook[EVIDENCIAS_SHEET]

    assert len(sheet.data_validations.dataValidation) == 2
    formulas = {dv.formula1 for dv in sheet.data_validations.dataValidation}
    assert any("Pendente" in f for f in formulas)
    assert any("Planilha original" in f for f in formulas)


def test_evidencias_sheet_skipped_when_no_configs() -> None:
    summaries = [_summary("INMS-1.1", "INMS 1.1")]
    workbook = build_report_workbook("2026-06", summaries)

    assert EVIDENCIAS_SHEET not in workbook.sheetnames
