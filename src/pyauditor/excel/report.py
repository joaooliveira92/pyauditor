"""Builds the consolidated Excel final: `INMS_BASE` + the 4 per-group tabs
(docs/spreadsheet.md §Abas 4-8) + `GLOSAS` (spec §12), from the JSON
summaries `measure` writes alongside each ROM (`rom/summary.py`).

Scope note: this ticket's output does not copy the capa's `CAPA_E_CONTROLE`
sheet into this workbook. The capa is a separate deliverable (spec §13);
`report` only requires it to exist first (fails clearly otherwise), as the
operational signal that `bootstrap` has run for this contract — and, for
`GLOSAS`, as the source of `valor-base` (spec §12.2).
"""

from pathlib import Path
from typing import Final

from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from pyauditor.excel._style import BODY_FONT, BOTTOM_BORDER, HEADER_FILL, HEADER_FONT, LEFT_ALIGN
from pyauditor.excel.glosas import compute_glosa
from pyauditor.excel.groups import GROUP_TABS, primary_group
from pyauditor.rom.summary import IndicatorSummary

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

# spec.md §12.3 — exactly these 7 columns; the fiscal-manual columns from
# docs/spreadsheet.md §Aba 10 (faixa de descumprimento, reincidência,
# justificativa, etc.) are out of this ticket's scope, not blanked in here.
_GLOSAS_COLUMNS: Final[tuple[str, ...]] = (
    "Competência",
    "Σ Pontos_NMS do mês",
    "Percentual de ajuste",
    "Valor-base",
    "Valor da glosa",
    "Teto atingido?",
    "Saldo rolado para o mês seguinte (p.p.)",
)

CellValue = str | float | int | None


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


def _inms_base_row(competencia: str, summary: IndicatorSummary) -> tuple[CellValue, ...]:
    diferenca_para_meta: float | None = None
    if summary.target_value is not None:
        diferenca_para_meta = summary.target_value - summary.result_pct

    return (
        competencia,
        None,  # Item contratual — fiscal-manual
        None,  # Serviço — fiscal-manual
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
        summary.orgao,
        round(summary.result_pct, 2),
        summary.target_value,
        "Conforme" if summary.conforms else "Não conforme",
        round(summary.penalty_points, 2),
    )


def build_report_workbook(
    competencia: str,
    summaries: list[IndicatorSummary],
    valor_base: float | None = None,
    *,
    is_final_month: bool = False,
) -> Workbook:
    """Builds the INMS_BASE + group tabs + GLOSAS workbook in memory — pure, no I/O."""
    workbook = Workbook()
    default_sheet = workbook.active
    assert default_sheet is not None
    workbook.remove(default_sheet)

    base_sheet = _new_sheet(workbook, INMS_BASE_SHEET, _INMS_BASE_COLUMNS, width=20)
    for row_idx, summary in enumerate(sorted(summaries, key=lambda s: s.contractual_id), start=2):
        _write_row(base_sheet, row_idx, _inms_base_row(competencia, summary))

    by_group: dict[str, list[IndicatorSummary]] = {group: [] for group in GROUP_TABS}
    for summary in summaries:
        group = primary_group(summary.contractual_id)
        if group is not None:
            by_group[group].append(summary)

    for group in GROUP_TABS:
        sheet = _new_sheet(workbook, group, _GROUP_TAB_COLUMNS, width=22)
        rows = sorted(by_group[group], key=lambda s: s.contractual_id)
        for row_idx, summary in enumerate(rows, start=2):
            _write_row(sheet, row_idx, _group_row(summary))

    glosas_sheet = _new_sheet(workbook, GLOSAS_SHEET, _GLOSAS_COLUMNS, width=26)
    total_points = sum(summary.penalty_points for summary in summaries)
    glosa = compute_glosa(total_points, valor_base, is_final_month=is_final_month)
    _write_row(
        glosas_sheet,
        2,
        (
            competencia,
            round(glosa.total_points, 2),
            round(glosa.percentual_ajuste, 5),
            glosa.valor_base,
            round(glosa.valor_da_glosa, 2) if glosa.valor_da_glosa is not None else None,
            "S" if glosa.teto_atingido else "N",
            round(glosa.saldo_rolado_pct, 5) if glosa.saldo_rolado_pct else None,
        ),
    )

    return workbook


def build_report(
    competencia: str,
    summaries: list[IndicatorSummary],
    output_path: Path,
    valor_base: float | None = None,
    *,
    is_final_month: bool = False,
) -> None:
    workbook = build_report_workbook(competencia, summaries, valor_base, is_final_month=is_final_month)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output_path)
