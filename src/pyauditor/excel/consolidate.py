"""Builds the consolidated financial workbook for `pyauditor consolidate`
(2.1): `CAPA_E_CONTROLE` + `SERVICOS_POR_ORGAO` + `INMS_BASE` + `GLOSAS` +
`CALCULO_PAGAMENTO` — the núcleo financeiro decided in
.scratch/multi-org-pipeline tickets 01/02/04.

`consolidate` never re-runs `measure`/`report`: its precondition is that
`reports/relatorio_<comp>_MinC.xlsx` and `_MTur.xlsx` already exist (ticket
04 Q1) — this module reads the fiscal-filled `CAPA_E_CONTROLE` from each, but
sources indicator-level `penalty_points` from the per-órgão
`roms/<orgao>/<comp>/*.json` summaries instead of the report workbook's
`INMS_BASE`. That tab deliberately leaves its glosa columns blank per
indicator (spec §12: glosa is a monthly aggregate there, not per-indicator),
so it can't carry the per-(indicador×órgão) detail ticket 02's `GLOSAS`
layout needs. The ROM JSONs are the same already-computed, read-only
artifact `report.py` itself was built from — reading them isn't re-running
`measure`, and both órgãos' ROMs are already a precondition of their report
workbooks existing.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Border, Font, Side

from pyauditor.codes import format_inms_code
from pyauditor.excel._style import (
    BODY_FONT,
    BOTTOM_BORDER,
    HEADER_FILL,
    HEADER_FONT,
    LABEL_FONT,
    LEFT_ALIGN,
    TITLE_FONT,
    CellValue,
)
from pyauditor.excel._style import UNIT_BY_SHAPE as _UNIT_BY_SHAPE
from pyauditor.excel._style import new_sheet as _new_sheet
from pyauditor.excel._style import write_row as _write
from pyauditor.excel.orgao_consolidation import with_orgao_consolidation
from pyauditor.logging import logger
from pyauditor.rom.summary import IndicatorSummary

CAPA_SHEET: Final = "CAPA_E_CONTROLE"
SERVICOS_SHEET: Final = "SERVICOS_POR_ORGAO"
INMS_BASE_SHEET: Final = "INMS_BASE"
GLOSAS_SHEET: Final = "GLOSAS"
CALCULO_SHEET: Final = "CALCULO_PAGAMENTO"

LIMITE_PCT: Final = 30.0  # teto único sobre o agregado dos dois órgãos (ticket 02)
RATEIO_PADRAO: Final = 0.5  # provisório, até fonte oficial (ticket 01/02)

# docs/styleguide.md number formats — currency and percent, zero as "-".
# `_style.py` doesn't carry these yet (production report.py/capa.py don't
# apply them either); local to this module until that becomes a shared need.
_CURRENCY_FMT: Final = "R$#,##0.00;R$#,##0.00;-"
# `result_pct`/`%Ajuste` are already stored in percent-space (95.5 meaning
# "95.5%"); the literal "%" symbol auto-multiplies by 100 on display, so it
# must be escaped for these. Only true 0-1 fractions (rateio) want the real,
# auto-scaling "%" format.
_PERCENT_FMT_SCALED: Final = '0.00"%";0.00"%";-'
_PERCENT_FMT_FRACTION: Final = "0.00%;0.00%;-"
_TOP_BORDER: Final = Border(top=Side(style="thin", color="1F2937"))

# Decisão Fiscal — o fiscal aceita a justificativa do fornecedor (anistia: a
# ocorrência sai da base de pontos) ou não aceita (glosa mantida). Ticket 02.
_DECISAO_ACEITA: Final = "aceita"

# GLOSAS: uma linha por (indicador × órgão) + resumo agregado (ticket 02).
_GLOSAS_COLUMNS: Final[tuple[str, ...]] = (
    "Competência", "Órgão", "Item Contratual", "Serviço", "Indicador",
    "Resultado", "Meta", "Faixa de Descumprimento", "Percentual de Ajuste",
    "Valor Base", "Valor Glosa", "Reincidência", "Justificativa",
    "Número da Ocorrência", "Decisão Fiscal", "Observação do Gestor",
)
# Colunas de decisão do fiscal — nunca recalculadas, só preservadas no merge.
_DECISION_COLUMNS: Final[tuple[str, ...]] = (
    "Reincidência", "Justificativa", "Número da Ocorrência",
    "Decisão Fiscal", "Observação do Gestor",
)
_DECISION_TEXT_COLUMNS: Final[tuple[int, ...]] = tuple(
    _GLOSAS_COLUMNS.index(name) + 1 for name in _DECISION_COLUMNS
)

_CALCULO_COLUMNS: Final[tuple[str, ...]] = ("Componente", "MinC", "MTur", "Consolidado")
_CALCULO_LINHAS: Final[tuple[str, ...]] = (
    "Percentual de rateio",
    "Valor bruto (= mensal × rateio)",
    "Pontos de glosa",
    "Valor da glosa (= MIN(pontos×0,001, 30%)/100 × bruto)",
    "Outros ajustes",
    "Valor recomendado (= max(0, bruto − glosa − outros))",
)

# docs spreadsheet.md's SERVICOS_POR_ORGAO — 9 serviços contratuais fixos
# (ticket 01). Segregação/critério de rateio idênticos para os dois órgãos
# até o Termo de Referência dizer o contrário.
_SERVICOS: Final[tuple[tuple[str, str, str, str], ...]] = (
    ("Central de Serviços e Monitoramento", "Sim", "Sim", "Sim"),
    ("Gerenciamento Técnico das Operações e Projetos", "Sim", "Sim", "Sim"),
    ("Banco de Dados", "Sim", "Sim", "Sim"),
    ("Aplicações, Virtualização e Computação em Nuvem", "Sim", "Sim", "Sim"),
    ("Serviços Corporativos", "Sim", "Sim", "Sim"),
    ("Armazenamento e Backup", "Sim", "Sim", "Sim"),
    ("Redes", "Sim", "Sim", "Sim"),
    ("Segurança da Informação", "Sim", "Sim", "Sim"),
    ("DevOps", "Sim", "Sim", "Sim"),
)

_CAPA_VALOR_LABELS: Final = ("Valor mensal vigente", "Valor global anual")

RowKey = tuple[str, str]  # (contractual_id, orgao)


@dataclass(frozen=True)
class ConsolidationResult:
    workbook: Workbook
    total_pontos: float
    glosa_final: float
    warnings: tuple[str, ...]


_TRACKED_HEADER_NAMES: Final[frozenset[str]] = frozenset({"Indicador", "Órgão", *_DECISION_COLUMNS})


def _check_no_duplicate_headers(path: Path, header_row: Sequence[object]) -> None:
    """A hand-edited workbook with a duplicate column name (two "Indicador"
    columns, or a stray column literally named "Justificativa" inserted by a
    fiscal) would otherwise make the header→index lookup silently keep the
    *last* matching column — decision values then get read from the wrong
    column with no error. Fail loudly instead."""
    seen: set[str] = set()
    duplicates: set[str] = set()
    for name in header_row:
        if isinstance(name, str) and name in _TRACKED_HEADER_NAMES:
            (duplicates if name in seen else seen).add(name)
    if duplicates:
        raise ValueError(
            f"{path}: coluna(s) duplicada(s) em {GLOSAS_SHEET!r}: {', '.join(sorted(duplicates))} — "
            "planilha hand-edited em formato inesperado, corrija antes de rodar consolidate de novo"
        )


def read_existing_decisions(path: Path) -> dict[RowKey, dict[str, object]]:
    """Reads the decision columns from a previously-generated consolidado
    workbook's `GLOSAS` sheet, keyed by (indicador, órgão) — the merge
    contract's preservation source (ticket 04 Q3). Empty dict if `path`
    doesn't exist yet or has no `GLOSAS` sheet (first run).
    """
    if not path.exists():
        return {}
    workbook = load_workbook(path, data_only=True)
    try:
        if GLOSAS_SHEET not in workbook.sheetnames:
            return {}
        sheet = workbook[GLOSAS_SHEET]

        header_row = [cell.value for cell in sheet[1]]
        if not header_row or "Indicador" not in header_row:
            return {}
        _check_no_duplicate_headers(path, header_row)
        col_idx = {name: i + 1 for i, name in enumerate(header_row) if isinstance(name, str)}
        indicador_col = col_idx.get("Indicador")
        orgao_col = col_idx.get("Órgão")
        if indicador_col is None or orgao_col is None:
            return {}

        decisions: dict[RowKey, dict[str, object]] = {}
        for row in range(2, sheet.max_row + 1):
            indicador = sheet.cell(row=row, column=indicador_col).value
            orgao = sheet.cell(row=row, column=orgao_col).value
            if not isinstance(indicador, str) or not isinstance(orgao, str):
                continue
            values: dict[str, object] = {
                name: sheet.cell(row=row, column=idx).value
                for name, idx in col_idx.items()
                if name in _DECISION_COLUMNS
            }
            if any(v not in (None, "") for v in values.values()):
                decisions[(format_inms_code(indicador), orgao)] = values
        return decisions
    finally:
        workbook.close()


def build_capa(
    wb: Workbook,
    competencia: str,
    minc_capa: dict[str, object],
    mtur_capa: dict[str, object],
    warnings: list[str],
) -> float | None:
    """Embeds a consolidated CAPA_E_CONTROLE — the contract is shared, so
    "Valor mensal vigente" should agree between the two órgão capas; MinC's
    value wins if they disagree, with a warning (never silently pick one).
    """
    ws = wb.create_sheet(CAPA_SHEET, 0)
    ws.sheet_view.showGridLines = False

    ws["A1"] = "Capa e controle — consolidado"
    ws["A1"].font = TITLE_FONT
    ws.merge_cells("A1:B1")

    ws["A3"] = "Campo"
    ws["B3"] = "Valor"
    for cell in (ws["A3"], ws["B3"]):
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = LEFT_ALIGN

    valor_base = _as_float(minc_capa.get("Valor mensal vigente"))
    mtur_valor = _as_float(mtur_capa.get("Valor mensal vigente"))
    if valor_base is not None and mtur_valor is not None and abs(valor_base - mtur_valor) > 0.01:
        warnings.append(
            f"'Valor mensal vigente' diverge entre MinC ({valor_base}) e MTur ({mtur_valor}) — usando MinC"
        )
    if valor_base is None:
        valor_base = mtur_valor

    campos: tuple[tuple[str, object], ...] = (
        ("Número do contrato", minc_capa.get("Número do contrato")),
        ("Processo SEI", minc_capa.get("Processo SEI")),
        ("Empresa contratada", minc_capa.get("Empresa contratada")),
        ("Órgãos contratantes", "Ministério da Cultura / Ministério do Turismo"),
        ("Competência", competencia),
        ("Valor mensal vigente", valor_base),
        ("Valor global anual", valor_base * 12 if valor_base is not None else None),
    )
    for offset, (label, value) in enumerate(campos):
        row = 4 + offset
        label_cell = ws.cell(row=row, column=1, value=label)
        label_cell.font = LABEL_FONT
        label_cell.alignment = LEFT_ALIGN
        label_cell.border = BOTTOM_BORDER

        value_cell = ws.cell(row=row, column=2, value=value)
        value_cell.font = BODY_FONT
        value_cell.border = BOTTOM_BORDER
        if label in _CAPA_VALOR_LABELS:
            value_cell.number_format = _CURRENCY_FMT

    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 42
    return valor_base


def build_servicos(wb: Workbook) -> None:
    ws = _new_sheet(
        wb, SERVICOS_SHEET,
        ("Item", "Serviço", "Prestado ao MinC?", "Prestado ao MTur?",
         "Segregação Obrigatória?", "Critério de Rateio"),
    )
    for i, (nome, minc, mtur, seg) in enumerate(_SERVICOS, start=2):
        _write(ws, i, (i - 1, nome, minc, mtur, seg, "Chamados, ativos ou valor definido"))


_INMS_BASE_COLUMNS: Final[tuple[str, ...]] = (
    "Competência", "Item contratual", "Serviço", "Grupo operacional",
    "Código INMS", "Descrição", "Órgão", "Meta mínima ou máxima",
    "Sentido da meta", "Numerador", "Denominador", "Resultado calculado",
    "Unidade", "Conformidade", "Diferença para a meta",
)

def _inms_base_row(competencia: str, summary: IndicatorSummary) -> tuple[CellValue, ...]:
    dif = None
    if summary.target_value is not None:
        dif = round(summary.target_value - summary.result_pct, 2)
    return (
        competencia, None, summary.asset, None, format_inms_code(summary.contractual_id),
        summary.name, summary.orgao, summary.target_value, summary.target_operator,
        summary.numerator, summary.denominator, round(summary.result_pct, 2),
        _UNIT_BY_SHAPE.get(summary.shape, ""),
        "Conforme" if summary.conforms else "Não conforme", dif,
    )


def build_inms_base(
    wb: Workbook, competencia: str, minc: list[IndicatorSummary], mtur: list[IndicatorSummary]
) -> None:
    """Pooling Σnum/Σden por indicador (ticket 02) — reusa a mesma regra que
    já era testada dentro de `report.py`, agora vivendo só aqui.
    """
    ws = _new_sheet(wb, INMS_BASE_SHEET, _INMS_BASE_COLUMNS, width=20)
    rows = with_orgao_consolidation(minc + mtur)
    rows.sort(key=lambda s: (s.contractual_id, s.asset or "", s.orgao))
    for row_idx, summary in enumerate(rows, start=2):
        _write(ws, row_idx, _inms_base_row(competencia, summary))
        # Percentuais: Meta / Resultado calculado / Diferença para a meta.
        if _UNIT_BY_SHAPE.get(summary.shape) == "%":
            for col in (8, 12, 15):
                ws.cell(row=row_idx, column=col).number_format = _PERCENT_FMT_SCALED


def _decision_value(decision: dict[str, object], key: str) -> CellValue:
    """`decision`'s values come from openpyxl cells (any scalar type it
    supports) — narrowed to what a fresh cell can hold, coercing anything
    unexpected (dates, etc.) to its string form rather than dropping it.
    """
    value = decision.get(key)
    if value is None or isinstance(value, str | int | float):
        return value
    return str(value)


def _faixa(summary: IndicatorSummary) -> str:
    if summary.target_operator is None or summary.target_value is None:
        return "Ocorrência sob detalhamento por-ativo" if summary.penalty_points > 0 else ""
    dif = (
        summary.target_value - summary.result_pct
        if summary.target_operator == ">="
        else summary.result_pct - summary.target_value
    )
    return f"Déficit de {dif:.2f}pp" if dif > 0 else "Não conforme"


def build_glosas(
    wb: Workbook,
    competencia: str,
    minc: list[IndicatorSummary],
    mtur: list[IndicatorSummary],
    valor_base: float | None,
    existing_decisions: dict[RowKey, dict[str, object]],
    warnings: list[str],
) -> tuple[float, float]:
    """GLOSAS — uma linha por (indicador × órgão) com ocorrência de glosa,
    mais o resumo agregado. Decisão do fiscal ('Aceita' = anistia) tira a
    ocorrência da base de pontos; colunas de decisão são preservadas do
    workbook anterior, nunca recalculadas (ticket 02/04 Q3).
    """
    ws = _new_sheet(wb, GLOSAS_SHEET, _GLOSAS_COLUMNS, width=26)
    seen_keys: set[RowKey] = set()
    row = 2
    total_pontos = 0.0

    for summary in minc + mtur:
        if summary.penalty_points <= 0:
            continue
        key: RowKey = (format_inms_code(summary.contractual_id), summary.orgao)
        seen_keys.add(key)
        decision = existing_decisions.get(key, {})
        is_amnestied = str(decision.get("Decisão Fiscal") or "").strip().lower().startswith(_DECISAO_ACEITA)

        pontos = summary.penalty_points
        if not is_amnestied:
            total_pontos += pontos
        pct = pontos * 0.001
        valor_glosa = round((valor_base or 0.0) * pct / 100, 2) if valor_base is not None else None

        _write(ws, row, (
            competencia, summary.orgao, "", "", format_inms_code(summary.contractual_id),
            round(summary.result_pct, 2), summary.target_value, _faixa(summary),
            round(pct, 4), valor_base, 0.0 if is_amnestied else valor_glosa,
            _decision_value(decision, "Reincidência"), _decision_value(decision, "Justificativa"),
            _decision_value(decision, "Número da Ocorrência"), _decision_value(decision, "Decisão Fiscal"),
            _decision_value(decision, "Observação do Gestor"),
        ))
        ws.cell(row=row, column=6).number_format = _PERCENT_FMT_SCALED
        ws.cell(row=row, column=7).number_format = _PERCENT_FMT_SCALED
        ws.cell(row=row, column=9).number_format = _PERCENT_FMT_SCALED
        if valor_base is not None:
            ws.cell(row=row, column=10).number_format = _CURRENCY_FMT
            ws.cell(row=row, column=11).number_format = _CURRENCY_FMT
        # Fiscal-entered free text round-trips across runs (ticket 04 Q3) —
        # the one column set most likely to accumulate copy-pasted content
        # over the contract's lifetime. Text format blocks formula injection
        # (a value starting with =+-@ would otherwise become a live formula
        # the next time this workbook is opened) without altering the text.
        for column in _DECISION_TEXT_COLUMNS:
            ws.cell(row=row, column=column).number_format = "@"
        row += 1

    for key, decision in existing_decisions.items():
        if key not in seen_keys:
            warnings.append(
                f"decisão registrada para {key[0]}/{key[1]} mas a ocorrência não existe mais nesta rodada — preservada apenas no histórico, não reescrita"
            )

    pct_bruto = total_pontos * 0.001
    aplicado = min(pct_bruto, LIMITE_PCT)
    glosa_final = (valor_base or 0.0) * aplicado / 100 if valor_base is not None else 0.0

    r = row + 2
    for label, value in (
        ("Total de Pontos", round(total_pontos, 2)),
        ("Fórmula (pontos × 0,001)", f"{pct_bruto:.4f}%"),
        ("Limite", f"{LIMITE_PCT:.1f}%"),
        ("Percentual Aplicado", f"{aplicado:.2f}%"),
        ("Valor Glosa", round(glosa_final, 2) if valor_base is not None else None),
    ):
        label_cell = ws.cell(row=r, column=1, value=label)
        value_cell = ws.cell(row=r, column=2, value=value)
        bold = label in ("Total de Pontos", "Valor Glosa")
        label_cell.font = Font(bold=True) if bold else BODY_FONT
        value_cell.font = Font(bold=True) if bold else BODY_FONT
        if label == "Total de Pontos":
            label_cell.border = _TOP_BORDER
            value_cell.border = _TOP_BORDER
        if label == "Valor Glosa" and valor_base is not None:
            value_cell.number_format = _CURRENCY_FMT
        r += 1

    return total_pontos, glosa_final


def build_calculo(
    wb: Workbook,
    valor_base: float | None,
    total_pontos: float,
    rateio_minc: float = RATEIO_PADRAO,
    rateio_mtur: float = RATEIO_PADRAO,
) -> None:
    """CALCULO_PAGAMENTO — espelha a inspiração: colunas MinC/MTur/
    Consolidado, glosa só na coluna Consolidado (ticket 02)."""
    ws = wb.create_sheet(CALCULO_SHEET)
    ws.sheet_view.showGridLines = False

    ws["A1"] = "Parâmetros de Entrada — rateio PROVISÓRIO até fonte oficial"
    base = valor_base or 0.0
    params: tuple[tuple[str, float, str], ...] = (
        ("Valor mensal vigente", base, _CURRENCY_FMT),
        ("Limite máximo de glosa (%)", LIMITE_PCT, _PERCENT_FMT_SCALED),
        ("Rateio MinC (provisório)", rateio_minc, _PERCENT_FMT_FRACTION),
        ("Rateio MTur (provisório)", rateio_mtur, _PERCENT_FMT_FRACTION),
    )
    for row, (param_label, param_value, param_fmt) in enumerate(params, start=3):
        ws.cell(row=row, column=1, value=param_label).font = Font(bold=True)
        value_cell = ws.cell(row=row, column=2, value=param_value)
        value_cell.font = BODY_FONT
        value_cell.number_format = param_fmt

    header_row = 9
    for i, col_name in enumerate(_CALCULO_COLUMNS, start=1):
        cell = ws.cell(row=header_row, column=i, value=col_name)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
    ws.column_dimensions["A"].width = 58

    colunas = (("MinC", rateio_minc, 0.0), ("MTur", rateio_mtur, 0.0), ("Consolidado", 1.0, total_pontos))
    total_row_idx = len(_CALCULO_LINHAS) - 1

    for idx, label in enumerate(_CALCULO_LINHAS):
        row = header_row + 1 + idx
        bold = idx == total_row_idx
        label_cell = ws.cell(row=row, column=1, value=label)
        label_cell.font = Font(bold=True) if bold else BODY_FONT
        if bold:
            label_cell.border = _TOP_BORDER
        fmt: str | None = None
        if label.startswith("Percentual de rateio"):
            fmt = _PERCENT_FMT_FRACTION
        elif label.startswith(("Valor bruto", "Valor da glosa", "Outros ajustes", "Valor recomendado")):
            fmt = _CURRENCY_FMT
        for col, (_nome, rateio, pontos) in zip(range(2, len(_CALCULO_COLUMNS) + 2), colunas):
            if label.startswith("Percentual de rateio"):
                value: object = rateio
            elif label.startswith("Valor bruto"):
                value = round(base * rateio, 2)
            elif label.startswith("Pontos de glosa"):
                value = round(pontos, 2)
            elif label.startswith("Valor da glosa"):
                value = round(min(pontos * 0.001, LIMITE_PCT) / 100 * base * rateio, 2) if pontos else 0.0
            elif label.startswith("Outros ajustes"):
                value = 0
            else:
                bruto = base * rateio
                glosa = min(pontos * 0.001, LIMITE_PCT) / 100 * bruto if pontos else 0.0
                value = round(max(0.0, bruto - glosa), 2)
            value_cell = ws.cell(row=row, column=col, value=value)
            value_cell.font = Font(bold=True) if bold else BODY_FONT
            if fmt:
                value_cell.number_format = fmt
            if bold:
                value_cell.border = _TOP_BORDER


def _as_float(value: object) -> float | None:
    return float(value) if isinstance(value, int | float) else None


def build_consolidated_workbook(
    competencia: str,
    minc: list[IndicatorSummary],
    mtur: list[IndicatorSummary],
    minc_capa: dict[str, object],
    mtur_capa: dict[str, object],
    existing_decisions: dict[RowKey, dict[str, object]] | None = None,
) -> ConsolidationResult:
    """Pure, in-memory build of the 5-sheet consolidated workbook."""
    warnings: list[str] = []
    wb = Workbook()
    default_sheet = wb.active
    assert default_sheet is not None
    wb.remove(default_sheet)

    valor_base = build_capa(wb, competencia, minc_capa, mtur_capa, warnings)
    build_servicos(wb)
    build_inms_base(wb, competencia, minc, mtur)
    total_pontos, glosa_final = build_glosas(
        wb, competencia, minc, mtur, valor_base, existing_decisions or {}, warnings
    )
    build_calculo(wb, valor_base, total_pontos)

    for warning in warnings:
        logger.warning(warning)

    return ConsolidationResult(workbook=wb, total_pontos=total_pontos, glosa_final=glosa_final, warnings=tuple(warnings))
