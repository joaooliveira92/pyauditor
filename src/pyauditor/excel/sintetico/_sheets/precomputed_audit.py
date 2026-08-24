"""Renderer básico das abas pré-computadas por-ativo (INMS 1.4/1.5, NOC/SOC
crítico e não-crítico; e 1.14, disponibilidade de infraestrutura — mesmo
shape `precomputed_table` com `name_column`) do `sintetico` — reconstruído
com o padrão de auditoria das abas INMS 1.1/1.2/1.3 (ticket 04 SRP).

INMS 1.14 pertence a duas categorias (`MONITORAMENTO_NOC_SOC` e
`OPERACAO_N3`) — a mesma tabela de serviços aparece uma vez por categoria
(produto cartesiano), como as demais abas de fila de atendimento fazem para
`Grupo_executor`.

A diferença do renderer pré-computado plano (`precomputed.py`), esta
variante emite seções de auditoria que a referência INMS 1.1 tem:

- **Seção 1** · Identificação (competência, contrato, fonte, datas).
- **Seção 2** · Resumo executivo: ativos avaliados, quantos atingiram a
  meta, penalidade total e situação geral do indicador — o equivalente ao
  "PONTUAÇÃO TOTAL" da tabela `MONITORAMENTO_NOC_SOC` (docs/spreadsheet.md).
- **Seção 3** · Tabela por sistema/serviço com o **resultado a 4 casas**
  (não 1, que arredondava 99,451 % → "99,5 %" e o fazia colidir com a meta),
  meta, desvio em p.p., faixas de 0,1 % e penalidade.
- **Seção 4** · Memória de cálculo da penalidade por linha.
- Nota de domínio: NOC/SOC é nível único N3 — este indicador não admite N1
  nem N2; por isso não se replica a Seção 5 (subtotais por nível) do
  INMS 1.1.
"""

from __future__ import annotations

from datetime import datetime
from math import isnan
from pathlib import Path
from typing import Final

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter as cl
from openpyxl.worksheet.worksheet import Worksheet

from pyauditor.config.categorias import CategoriasFile, WholeIndicatorMode
from pyauditor.config.models import PrecomputedTableCalculation
from pyauditor.engine.strategies import meets_target, parse_decimal
from pyauditor.excel._inms_audit_common._cells import header_row, section_bar
from pyauditor.excel._inms_audit_common._layout import (
    BODY_FONT,
    LABEL_FONT,
    NOTE_FONT,
    ORANGE_FILL,
    PCT4,
    TEAL_FILL,
)
from pyauditor.excel._inms_audit_common._section_1 import (
    write_section_1_identificacao,
)
from pyauditor.excel._safety import safe_excel_text
from pyauditor.excel.sintetico._sheets._shared import _NIVEL_BY_CATEGORIA
from pyauditor.periodo import PeriodoAfericao

__all__ = ('_write_precomputed_audit_sheet',)

_SECTION_2_COLUMNS: Final[tuple[str, ...]] = (
    'Categoria',
    'Sistema / Serviço',
    'Resultado',
    'Meta',
    'Desvio vs Meta',
    'Faixas 0,1%',
    'Penalidade',
    'Meta atingida?',
)
# Índices 1-based dentro de `_SECTION_2_COLUMNS` cuyo contenido es numérico.
_NUMERIC_COLS: Final[frozenset[int]] = frozenset({3, 4, 5, 6, 7})

# Anexo D (docs/spreadsheet.md): NOC/SOC penaliza a cada 0,1 p.p. — o passo
# não vive na config precomputed (só a penalidade final por ativo em
# `penalty_column`), então se declara aqui para a memória da Seção 3.
_STEP_PCT: Final[float] = 0.1

_RESUMO_START_ROW: Final[int] = 11

_COLUMN_WIDTHS: Final[dict[int, int]] = {
    1: 28,
    2: 34,
    3: 14,
    4: 12,
    5: 14,
    6: 12,
    7: 12,
    8: 16,
}


def _count_table_rows(
    entries: list[tuple[str, WholeIndicatorMode]],
    calculation: PrecomputedTableCalculation,
    rows: list[dict[str, str]],
) -> int:
    """Conta quantas linhas `_write_table` vai efetivamente escrever — mesmo
    filtro (valor presente e numérico), usado para dimensionar a Seção 2
    (resumo executivo) antes de a tabela existir na planilha."""
    count = 0
    for _categoria_key, _entry in entries:
        for data_row in rows:
            raw_value = data_row.get(calculation.result_column, '')
            if not raw_value.strip():
                continue
            if isnan(parse_decimal(raw_value)):
                continue
            count += 1
    return count


def _write_resumo_executivo(
    sheet: Worksheet, start_row: int, table_start: int, table_end: int
) -> int:
    """Seção 2 — resumo executivo: equivalente ao "PONTUAÇÃO TOTAL" da
    tabela `MONITORAMENTO_NOC_SOC` (docs/spreadsheet.md) — ativos avaliados,
    quantos atingiram a meta, penalidade total e situação geral do
    indicador. Formulas referenciam a Seção 3 (tabela por sistema/serviço)
    diretamente, para se manterem corretas se alguém editar uma linha ali."""
    section_bar(sheet, start_row, 'SEÇÃO 2 · RESUMO EXECUTIVO')
    header_row(
        sheet,
        start_row + 1,
        (
            'Ativos avaliados',
            'Atingiram a meta',
            'Não atingiram a meta',
            'Penalidade total',
            'Situação geral',
        ),
        numeric_cols=frozenset({1, 2, 3, 4}),
    )
    kpi_row = start_row + 2
    h_range = f'H{table_start}:H{table_end}'
    sheet.cell(row=kpi_row, column=1, value=f'=COUNTA({h_range})')
    sheet.cell(row=kpi_row, column=2, value=f'=COUNTIF({h_range},"Sim")')
    sheet.cell(row=kpi_row, column=3, value=f'=COUNTIF({h_range},"Não")')
    penal_cell = sheet.cell(
        row=kpi_row, column=4, value=f'=SUM(G{table_start}:G{table_end})'
    )
    penal_cell.number_format = '0'
    sheet.cell(
        row=kpi_row,
        column=5,
        value=f'=IF(C{kpi_row}=0,"Alcançado","Não alcançado")',
    )
    for col in range(1, 6):
        cell = sheet.cell(row=kpi_row, column=col)
        cell.font = Font(name='Arial', size=12, bold=True)
        cell.fill = TEAL_FILL
        cell.alignment = Alignment(horizontal='center')
    sheet.row_dimensions[kpi_row].height = 24
    return kpi_row + 2


def _write_table(
    sheet: Worksheet,
    start_row: int,
    categorias: CategoriasFile,
    entries: list[tuple[str, WholeIndicatorMode]],
    calculation: PrecomputedTableCalculation,
    target_operator: str,
    target_value: float,
    rows: list[dict[str, str]],
) -> int:
    """Escreve a tabela por sistema/serviço. Devolve a primeira linha livre.

    Cada linha guarda `resultado` e `meta` como fração real (formato PCT4) e
    as derivadas (desvio, faixas) como fórmulas que referenciam a própria
    linha, para auditoria viva na planilha."""
    section_bar(sheet, start_row, 'SEÇÃO 3 · DETALHE POR SISTEMA/SERVIÇO')
    header_row(
        sheet, start_row + 1, _SECTION_2_COLUMNS, numeric_cols=_NUMERIC_COLS
    )
    row = start_row + 2
    for categoria_key, _entry in entries:
        categoria = categorias.categorias[categoria_key]
        for data_row in rows:
            raw_value = data_row.get(calculation.result_column, '')
            if not raw_value.strip():
                continue
            value = parse_decimal(raw_value)
            if isnan(value):
                continue

            name = (
                data_row.get(calculation.name_column, '')
                if calculation.name_column
                else ''
            )
            penalidade_raw = (
                data_row.get(calculation.penalty_column, '')
                if calculation.penalty_column
                else ''
            )
            penalidade = (
                parse_decimal(penalidade_raw) if penalidade_raw.strip() else 0.0
            )
            if isnan(penalidade):
                penalidade = 0.0
            atingido = meets_target(value, target_operator, target_value)

            cell_cat = sheet.cell(row=row, column=1, value=categoria.label)
            cell_cat.font = BODY_FONT
            cell_name = sheet.cell(
                row=row, column=2, value=safe_excel_text(name)
            )
            cell_name.font = BODY_FONT
            cell_res = sheet.cell(row=row, column=3, value=value / 100)
            cell_res.number_format = PCT4
            cell_meta = sheet.cell(row=row, column=4, value=target_value / 100)
            cell_meta.number_format = PCT4
            # Desvio vs Meta (Meta - Resultado), positivo cuando queda bajo.
            cell_dev = sheet.cell(row=row, column=5, value=f'=D{row}-C{row}')
            cell_dev.number_format = PCT4
            sheet.cell(
                row=row,
                column=6,
                value=(f'=IF(E{row}<=0,0,ROUNDUP(E{row}*100/{_STEP_PCT:g},0))'),
            ).number_format = '0'
            sheet.cell(row=row, column=7, value=penalidade).number_format = '0'
            sheet.cell(row=row, column=8, value='Sim' if atingido else 'Não')
            row += 1
    return row


def _write_memoria_penalidad(
    sheet: Worksheet,
    start_row: int,
    categorias: CategoriasFile,
    entries: list[tuple[str, WholeIndicatorMode]],
    calculation: PrecomputedTableCalculation,
    target_operator: str,
    target_value: float,
    rows: list[dict[str, str]],
    first_data_row: int,
) -> None:
    """Seção 4 — memória de penalidade por linha (referencia as fórmulas da
    Seção 3). `first_data_row` é a primeira linha de dados da Seção 3 (não a
    primeira linha livre depois dela) — usada tanto no rótulo "(linha N)"
    quanto nas fórmulas `=E{row_idx}`/`=F{row_idx}` que apontam de volta
    para a linha correspondente da tabela."""
    section_bar(sheet, start_row, 'SEÇÃO 4 · MEMÓRIA DA PENALIDADE')
    row = start_row + 1
    row_idx = first_data_row
    for _categoria, _entry in entries:
        for data_row in rows:
            raw_value = data_row.get(calculation.result_column, '')
            if not raw_value.strip():
                continue
            value = parse_decimal(raw_value)
            if isnan(value):
                continue
            penalidade_raw = (
                data_row.get(calculation.penalty_column, '')
                if calculation.penalty_column
                else ''
            )
            penalidade = (
                parse_decimal(penalidade_raw) if penalidade_raw.strip() else 0.0
            )
            if isnan(penalidade):
                penalidade = 0.0
            atingido = meets_target(value, target_operator, target_value)

            name = (
                data_row.get(calculation.name_column, '')
                if calculation.name_column
                else ''
            )
            label = safe_excel_text(name) if name else f'Ativo {row_idx}'
            head = sheet.cell(
                row=row, column=1, value=f'{label} (linha {row_idx})'
            )
            head.font = LABEL_FONT

            sheet.cell(row=row + 1, column=1, value='Meta:').font = BODY_FONT
            cell = sheet.cell(row=row + 1, column=2, value=target_value / 100)
            cell.number_format = PCT4
            sheet.cell(
                row=row + 1, column=3, value='Resultado:'
            ).font = BODY_FONT
            cell = sheet.cell(row=row + 1, column=4, value=value / 100)
            cell.number_format = PCT4

            sheet.cell(
                row=row + 2, column=1, value='Desvio (p.p.):'
            ).font = BODY_FONT
            cell = sheet.cell(row=row + 2, column=2, value=f'=E{row_idx}*100')
            cell.number_format = '0.0000'
            sheet.cell(
                row=row + 2, column=3, value='Faixas 0,1%:'
            ).font = BODY_FONT
            cell = sheet.cell(row=row + 2, column=4, value=f'=F{row_idx}')
            cell.number_format = '0'

            sheet.cell(
                row=row + 3, column=1, value='Penalidade:'
            ).font = BODY_FONT
            cell = sheet.cell(row=row + 3, column=2, value=penalidade)
            cell.number_format = '0'
            sheet.cell(
                row=row + 3, column=3, value='Meta atingida?'
            ).font = BODY_FONT
            sheet.cell(
                row=row + 3, column=4, value='Sim' if atingido else 'Não'
            )

            row += 5
            row_idx += 1


def _write_note_nivel(
    sheet: Worksheet, row: int, entries: list[tuple[str, WholeIndicatorMode]]
) -> None:
    niveis = sorted({_NIVEL_BY_CATEGORIA.get(ck, '—') for ck, _e in entries})
    niveis_str = '; '.join(niveis)
    sheet.merge_cells(start_row=row, start_column=1, end_row=row, end_column=8)
    cell = sheet.cell(
        row=row,
        column=1,
        value=(
            f'Categoria(s) desta aba → nível único {niveis_str}. Este '
            'indicador não admite N1 nem N2; por isso não há subtotais '
            'por nível nesta aba.'
        ),
    )
    cell.font = NOTE_FONT
    cell.fill = ORANGE_FILL
    cell.alignment = Alignment(wrap_text=True)


def _write_precomputed_audit_sheet(
    workbook: Workbook,
    sheet_name: str,
    categorias: CategoriasFile,
    entries: list[tuple[str, WholeIndicatorMode]],
    calculation: PrecomputedTableCalculation,
    target_operator: str,
    target_value: float,
    rows: list[dict[str, str]],
    contract: str,
    periodo: PeriodoAfericao | None,
    raw_csv_path: Path,
    generated_at: datetime,
) -> None:
    sheet = workbook.create_sheet(title=sheet_name)
    sheet.sheet_view.showGridLines = False
    for col, width in _COLUMN_WIDTHS.items():
        sheet.column_dimensions[cl(col)].width = width

    labels = dict.fromkeys(
        categorias.categorias[ck].label for ck, _e in entries
    )
    label = ' / '.join(labels)
    write_section_1_identificacao(
        sheet,
        title=f'{safe_excel_text(label)} – Disponibilidade de sistema/serviço',
        rows=rows,
        contract=contract,
        periodo=periodo,
        raw_csv_path=raw_csv_path,
        generated_at=generated_at,
    )

    row_count = _count_table_rows(entries, calculation, rows)
    # Layout fixo: Seção 2 (resumo) ocupa 4 linhas (bar, cabeçalho, KPI,
    # espaço) a partir de `_RESUMO_START_ROW`; a tabela da Seção 3 começa
    # logo em seguida (bar + cabeçalho, 2 linhas) antes da primeira linha de
    # dados — usado para que o resumo já saiba o range a somar antes de a
    # tabela existir na planilha.
    table_section_start = _RESUMO_START_ROW + 4
    table_data_start = table_section_start + 2
    table_data_end = table_data_start + max(row_count, 1) - 1
    _write_resumo_executivo(
        sheet,
        start_row=_RESUMO_START_ROW,
        table_start=table_data_start,
        table_end=table_data_end,
    )

    table_first_data_row = table_section_start + 2
    next_free_row = _write_table(
        sheet,
        start_row=table_section_start,
        categorias=categorias,
        entries=entries,
        calculation=calculation,
        target_operator=target_operator,
        target_value=target_value,
        rows=rows,
    )
    _write_memoria_penalidad(
        sheet,
        start_row=next_free_row + 2,
        categorias=categorias,
        entries=entries,
        calculation=calculation,
        target_operator=target_operator,
        target_value=target_value,
        rows=rows,
        first_data_row=table_first_data_row,
    )
    _write_note_nivel(sheet, sheet.max_row + 2, entries)
