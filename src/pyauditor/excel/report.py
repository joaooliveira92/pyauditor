"""Builds the consolidated Excel final: `CAPA_E_CONTROLE` (first sheet) +
`CADASTROS` + `INMS_BASE` + the 4 per-group tabs (docs/spreadsheet.md
§Abas 1-2, 4-8) + `GLOSAS` (spec §12) + `EVIDENCIAS` (spec §Aba 9),
from the JSON summaries `measure` writes alongside each ROM
(`rom/summary.py`) and the capa workbook `bootstrap` created.
"""

from pathlib import Path
from typing import Final

from openpyxl import Workbook
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.worksheet import Worksheet

from pyauditor.config.models import IndicatorConfig
from pyauditor.excel._style import BODY_FONT, BOTTOM_BORDER, HEADER_FILL, HEADER_FONT, LEFT_ALIGN
from pyauditor.excel.capa import SHEET_NAME as CAPA_SHEET_NAME
from pyauditor.excel.capa import render_capa_sheet
from pyauditor.excel.glosas import (
    GlosaResult,
    Historico,
    compute_glosa,
    houve_reincidencia,
    saldo_anterior_pct_de,
)
from pyauditor.excel.groups import GROUP_TABS, primary_group
from pyauditor.rom.summary import IndicatorSummary

CADASTROS_SHEET: Final = "CADASTROS"
EVIDENCIAS_SHEET: Final = "EVIDENCIAS"
INMS_BASE_SHEET: Final = "INMS_BASE"
GLOSAS_SHEET: Final = "GLOSAS"

# docs/spreadsheet.md §Aba 4 "Colunas propostas" — every column, in order.
# Columns not derivable from a measurement (fiscal-manual-entry-only) stay
# blank rather than being fabricated, per this ticket's scope.
_INMS_BASE_COLUMNS: Final[tuple[str, ...]] = (
    "Competência",
    "Item contratual",
    "Serviço",
    "Grupo operacional",
    "Código INMS",
    "Descrição",
    "Órgão",
    "Meta mínima ou máxima",
    "Sentido da meta",
    "Numerador",
    "Denominador",
    "Resultado calculado",
    "Unidade",
    "Aplicabilidade",
    "Resultado esperado",
    "Conformidade",
    "Diferença para a meta",
    "Ocorrência de glosa",
    "Percentual de glosa",
    "Valor-base",
    "Valor da glosa",
    "Justificativa",
    "Referência da evidência",
    "Número SEI",
    "Responsável pela evidência",
    "Observação do fiscal",
)

_GROUP_TAB_COLUMNS: Final[tuple[str, ...]] = (
    "Código INMS",
    "Descrição",
    "Serviço",
    "Órgão",
    "Resultado (%)",
    "Meta",
    "Conformidade",
    "Penalidade (pontos)",
)

_UNIT_BY_SHAPE: Final[dict[str, str]] = {
    "ratio": "%",
    "segmented_ratio": "%",
    "count_difference": "unidades",
    "external_catalog_sum": "pontos",
}

# spec.md §12.3, plus rollover/reincidência (.scratch/framework-audit/issues/
# 11-estado-persistente-entre-competencias.md): saldo do mês anterior consumido
# no cálculo e a flag de reincidência (item 35 do TR — 3+ estouros do teto em
# 6 meses = inexecução parcial do contrato; não altera o valor da glosa). As
# demais colunas fiscal-manual de docs/spreadsheet.md §Aba 10 (faixa de
# descumprimento, justificativa, etc.) seguem fora deste escopo.
_GLOSAS_COLUMNS: Final[tuple[str, ...]] = (
    "Competência",
    "Σ Pontos_NMS do mês",
    "Saldo recebido do mês anterior (p.p.)",
    "Percentual de ajuste",
    "Valor-base",
    "Valor da glosa",
    "Teto atingido?",
    "Saldo rolado para o mês seguinte (p.p.)",
    "Reincidência (3x/6m)?",
)

_CADASTROS_COLUMNS: Final[tuple[str, ...]] = (
    "Código INMS",
    "Descrição",
    "Formato",
    "Meta",
    "Sentido",
    "Penalidade (pontos base)",
    "Penalidade (p.p. por descumprimento)",
)

_EVIDENCIAS_COLUMNS: Final[tuple[str, ...]] = (
    "Competência",
    "Código INMS",
    "Tipo de evidência",
    "Descrição",
    "Fonte/URL",
    "Responsável pela coleta",
    "Data de coleta",
    "Status",
)

_EVIDENCIAS_TIPOS: Final[tuple[str, ...]] = (
    "Planilha original",
    "Print de sistema",
    "Documento SEI",
    "E-mail de confirmação",
    "Relatório de monitoramento",
    "Foto/registro visual",
    "Outro",
)

_EVIDENCIAS_STATUS: Final[tuple[str, ...]] = (
    "Pendente",
    "Coletada",
    "Validada",
)

CellValue = str | float | int | None


def _sort_key(summary: IndicatorSummary) -> tuple[str, str]:
    # Multi-asset rows (spec/ticket "multi-asset file discovery") share a
    # contractual_id, so sort by asset within it for a stable, readable order.
    return (summary.contractual_id, summary.asset or "")


def _new_sheet(workbook: Workbook, name: str, columns: tuple[str, ...], width: int) -> Worksheet:
    sheet: Worksheet = workbook.create_sheet(name)
    sheet.sheet_view.showGridLines = False
    for col_idx, column in enumerate(columns, start=1):
        cell = sheet.cell(row=1, column=col_idx, value=column)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = LEFT_ALIGN
        sheet.column_dimensions[cell.column_letter].width = width
    sheet.freeze_panes = "A2"
    return sheet


def _write_row(sheet: Worksheet, row_idx: int, values: tuple[CellValue, ...]) -> None:
    for col_idx, value in enumerate(values, start=1):
        cell = sheet.cell(row=row_idx, column=col_idx, value=value)
        cell.font = BODY_FONT
        cell.border = BOTTOM_BORDER


def _cadastros_row(config: IndicatorConfig) -> tuple[CellValue, ...]:
    target = config.target
    penalty = config.penalty
    return (
        config.indicator.contractual_id,
        config.indicator.name,
        config.calculation.shape,
        target.value if target is not None else None,
        target.operator if target is not None else None,
        penalty.base_points if penalty is not None else None,
        penalty.step_points if penalty is not None else None,
    )


def _evidencias_row(competencia: str, config: IndicatorConfig) -> tuple[CellValue, ...]:
    return (
        competencia,
        config.indicator.contractual_id,
        None,  # Tipo de evidência — fiscal-manual
        None,  # Descrição — fiscal-manual
        None,  # Fonte/URL — fiscal-manual
        None,  # Responsável pela coleta — fiscal-manual
        None,  # Data de coleta — fiscal-manual
        "Pendente",
    )


def _build_evidencias_sheet(
    workbook: Workbook,
    competencia: str,
    configs: list[IndicatorConfig],
) -> None:
    sheet = _new_sheet(workbook, EVIDENCIAS_SHEET, _EVIDENCIAS_COLUMNS, width=24)
    sorted_configs = sorted(configs, key=lambda c: c.indicator.contractual_id)
    for row_idx, config in enumerate(sorted_configs, start=2):
        _write_row(sheet, row_idx, _evidencias_row(competencia, config))

    tipo_col = 3  # "Tipo de evidência"
    status_col = 8  # "Status"
    max_row = len(sorted_configs) + 1

    tipo_validation = DataValidation(
        type="list",
        formula1=f'"{",".join(_EVIDENCIAS_TIPOS)}"',
        allow_blank=True,
    )
    sheet.add_data_validation(tipo_validation)
    tipo_validation.add(f"C2:C{max_row}")

    status_validation = DataValidation(
        type="list",
        formula1=f'"{",".join(_EVIDENCIAS_STATUS)}"',
        allow_blank=False,
    )
    sheet.add_data_validation(status_validation)
    status_validation.add(f"H2:H{max_row}")


def _inms_base_row(competencia: str, summary: IndicatorSummary) -> tuple[CellValue, ...]:
    diferenca_para_meta: float | None = None
    if summary.target_value is not None:
        diferenca_para_meta = summary.target_value - summary.result_pct

    return (
        competencia,
        None,  # Item contratual — fiscal-manual
        summary.asset,  # None for single-asset indicators
        primary_group(summary.contractual_id),
        summary.contractual_id,
        summary.name,
        summary.orgao,
        summary.target_value,
        summary.target_operator,
        summary.numerator,
        summary.denominator,
        round(summary.result_pct, 2),
        _UNIT_BY_SHAPE.get(summary.shape, ""),
        None,  # Aplicabilidade — fiscal-manual
        None,  # Resultado esperado — fiscal-manual
        "Conforme" if summary.conforms else "Não conforme",
        round(diferenca_para_meta, 2) if diferenca_para_meta is not None else None,
        None,  # Ocorrência de glosa — glosa é um agregado mensal (GLOSAS), não por indicador (spec §12)
        None,  # Percentual de glosa — idem
        None,  # Valor-base — idem
        None,  # Valor da glosa — idem
        None,  # Justificativa — fiscal-manual
        None,  # Referência da evidência — fiscal-manual
        None,  # Número SEI — fiscal-manual
        None,  # Responsável pela evidência — fiscal-manual
        None,  # Observação do fiscal — fiscal-manual
    )


def _group_row(summary: IndicatorSummary) -> tuple[CellValue, ...]:
    return (
        summary.contractual_id,
        summary.name,
        summary.asset,
        summary.orgao,
        round(summary.result_pct, 2),
        summary.target_value,
        "Conforme" if summary.conforms else "Não conforme",
        round(summary.penalty_points, 2),
    )


def compute_report_glosa(
    competencia: str,
    summaries: list[IndicatorSummary],
    valor_base: float | None,
    *,
    is_final_month: bool = False,
    historico: Historico | None = None,
) -> GlosaResult:
    """The same glosa the GLOSAS sheet renders, exposed so `cli/report.py`
    can persist it to `roms/<orgao>/glosa_historico.json` after a successful
    `report` run without recomputing the rollover/reincidência logic itself.
    """
    total_points = sum(summary.penalty_points for summary in summaries)
    saldo_anterior = saldo_anterior_pct_de(historico or {}, competencia)
    return compute_glosa(
        total_points, valor_base, is_final_month=is_final_month, saldo_anterior_pct=saldo_anterior
    )


def build_report_workbook(
    competencia: str,
    summaries: list[IndicatorSummary],
    valor_base: float | None = None,
    *,
    is_final_month: bool = False,
    capa_fields: dict[str, object] | None = None,
    configs: list[IndicatorConfig] | None = None,
    historico: Historico | None = None,
) -> Workbook:
    """Builds the CAPA_E_CONTROLE + CADASTROS + INMS_BASE + group tabs +
    GLOSAS + EVIDENCIAS workbook in memory — pure, no I/O. `capa_fields`
    (from `capa.read_capa_fields`) is optional so callers/tests that don't
    care about the capa tab can omit it; `report`'s CLI always passes it
    since `bootstrap` is a required precondition. `configs` (from
    `pipeline.discover_configs`) powers the CADASTROS and EVIDENCIAS tabs;
    when omitted both tabs are skipped (backward-compatible with callers
    that don't supply it). `historico` (from `glosas.read_historico`) feeds
    rollover (`saldo_anterior_pct`) and the reincidência flag; when omitted
    both default to "no prior history" (0.0 saldo, no reincidência).
    """
    workbook = Workbook()
    default_sheet = workbook.active
    assert default_sheet is not None
    workbook.remove(default_sheet)

    if capa_fields is not None:
        capa_sheet = workbook.create_sheet(CAPA_SHEET_NAME, 0)
        render_capa_sheet(capa_sheet, capa_fields)

    if configs:
        cadastros_sheet = _new_sheet(workbook, CADASTROS_SHEET, _CADASTROS_COLUMNS, width=28)
        for row_idx, config in enumerate(sorted(configs, key=lambda c: c.indicator.contractual_id), start=2):
            _write_row(cadastros_sheet, row_idx, _cadastros_row(config))

    # MinC/MTur pooling lives in `consolidate` (2.1), not here — this report
    # is per-órgão by construction (`run_report` only ever loads one órgão's
    # ROMs), so `summaries` never mixes MinC+MTur in practice. See
    # `pyauditor.excel.consolidate` and .scratch/multi-org-pipeline ticket 02.
    base_sheet = _new_sheet(workbook, INMS_BASE_SHEET, _INMS_BASE_COLUMNS, width=20)
    for row_idx, summary in enumerate(sorted(summaries, key=_sort_key), start=2):
        _write_row(base_sheet, row_idx, _inms_base_row(competencia, summary))

    by_group: dict[str, list[IndicatorSummary]] = {group: [] for group in GROUP_TABS}
    for summary in summaries:
        group = primary_group(summary.contractual_id)
        if group is not None:
            by_group[group].append(summary)

    for group in GROUP_TABS:
        sheet = _new_sheet(workbook, group, _GROUP_TAB_COLUMNS, width=22)
        rows = sorted(by_group[group], key=_sort_key)
        for row_idx, summary in enumerate(rows, start=2):
            _write_row(sheet, row_idx, _group_row(summary))

    glosas_sheet = _new_sheet(workbook, GLOSAS_SHEET, _GLOSAS_COLUMNS, width=26)
    historico = historico or {}
    saldo_anterior = saldo_anterior_pct_de(historico, competencia)
    glosa = compute_report_glosa(
        competencia, summaries, valor_base, is_final_month=is_final_month, historico=historico
    )
    reincidencia = houve_reincidencia(historico, competencia, glosa.teto_atingido)
    _write_row(
        glosas_sheet,
        2,
        (
            competencia,
            round(glosa.total_points, 2),
            round(saldo_anterior, 5) if saldo_anterior else None,
            round(glosa.percentual_ajuste, 5),
            glosa.valor_base,
            round(glosa.valor_da_glosa, 2) if glosa.valor_da_glosa is not None else None,
            "S" if glosa.teto_atingido else "N",
            round(glosa.saldo_rolado_pct, 5) if glosa.saldo_rolado_pct else None,
            "S" if reincidencia else "N",
        ),
    )

    if configs:
        _build_evidencias_sheet(workbook, competencia, configs)

    return workbook


def build_report(
    competencia: str,
    summaries: list[IndicatorSummary],
    output_path: Path,
    valor_base: float | None = None,
    *,
    is_final_month: bool = False,
    capa_fields: dict[str, object] | None = None,
    configs: list[IndicatorConfig] | None = None,
    historico: Historico | None = None,
) -> None:
    workbook = build_report_workbook(
        competencia, summaries, valor_base,
        is_final_month=is_final_month, capa_fields=capa_fields,
        configs=configs, historico=historico,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        workbook.save(output_path)
    finally:
        workbook.close()
