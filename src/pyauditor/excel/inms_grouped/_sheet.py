"""Escrita das linhas já montadas (`_rows.py`) no worksheet e aplicação do
agrupamento nativo do Excel (Dados > Agrupar) — a única responsabilidade
deste módulo é a interação com `openpyxl`, sem nenhuma aritmética de
domínio.
"""

from __future__ import annotations

from openpyxl.worksheet.worksheet import Worksheet

from pyauditor.excel._style import BODY_FONT, LABEL_FONT, CellValue

from ._rows import _is_subtotal_label
from ._types import _COLUMNS, _PERCENT_FMT, _TOP_BORDER


def _write_rows(ws: Worksheet, final_rows: list[list[CellValue]]) -> None:
    for row_idx, values in enumerate(final_rows, start=2):
        label = values[1]
        is_subtotal = _is_subtotal_label(label, prefix='Consolidado')
        for c, v in enumerate(values, start=1):
            cell = ws.cell(row_idx, c, v)
            cell.font = LABEL_FONT if is_subtotal else BODY_FONT
            if c in (8, 12, 15) and isinstance(v, int | float):
                cell.number_format = _PERCENT_FMT
        if is_subtotal:
            for c in range(1, len(_COLUMNS) + 1):
                ws.cell(row_idx, c).border = _TOP_BORDER


def _apply_breakdown_outline(
    ws: Worksheet, r: int, block: list[list[CellValue]]
) -> int:
    """Agrupamento de um bloco com detalhamento.

    Quando existe total geral (rótulo exatamente `"Consolidado"` —
    `_CodeInfo.consolidatable=True`, hoje sempre o caso para os INMS com
    detalhamento), ele é o único nível 0 e cada `"Consolidado - {órgão}"` é
    nível 1, filho dele — um único pai com dois filhos, `Consolidado -
    MinC` e `Consolidado - MTur`.

    Quando não existe (`consolidatable=False` — nenhum código usa isso
    hoje, mas a função continua correta se algum dia usar), os
    `"Consolidado - {órgão}"` viram **irmãos**: todos nível 0, nenhum
    filho do outro — Excel não deixa recolher um irmão de nível 0 sob o
    outro sem um pai comum, e inventar um pai aqui sugeriria uma relação
    entre órgãos que a apuração não valida. Cada um continua com seu
    próprio detalhe recolhido (nível 1 neste caso, em vez de 2).

    Devolve a quantidade de subgrupos `"Consolidado - {órgão}"` criados
    (não conta o total geral, quando existe)."""
    n = len(block)
    has_grand = block[0][1] == 'Consolidado'
    n_subgroups = 0
    offset = 0
    while offset < n:
        header_row = r + offset
        is_grand_row = has_grand and offset == 0
        level = 0 if (is_grand_row or not has_grand) else 1
        ws.row_dimensions[header_row].outlineLevel = level
        ws.row_dimensions[header_row].hidden = has_grand and level != 0
        if not is_grand_row:
            n_subgroups += 1
        offset += 1
        detail_start = offset
        detail_level = level + 1
        while offset < n and not _is_subtotal_label(
            block[offset][1], prefix='Consolidado'
        ):
            ws.row_dimensions[r + offset].outlineLevel = detail_level
            ws.row_dimensions[r + offset].hidden = True
            offset += 1
        if offset > detail_start:
            ws.row_dimensions[header_row].collapsed = True
    if has_grand and n > 1:
        ws.row_dimensions[r].collapsed = True
    return n_subgroups


def _apply_outline(
    ws: Worksheet,
    code_blocks: list[tuple[str, list[list[CellValue]]]],
) -> int:
    """Agrupamento nativo por Código INMS. Todo bloco cuja primeira linha é
    um cabeçalho `"Consolidado"`/`"Consolidado - {órgão}"` (detalhado ou
    verbatim reorganizado por `_restructure_verbatim`) passa por
    `_apply_breakdown_outline` — mesma hierarquia pai/filho em todos os
    casos. Os poucos blocos que `_restructure_verbatim` não conseguiu
    reorganizar (formato inesperado, ex. só uma linha ou nenhuma por
    órgão) caem no fallback verbatim: nível 0 = 1ª linha; nível 1 = demais
    valores distintos de Órgão; nível 2 = repetições. `summaryBelow=False`
    (setado pelo chamador) mantém a linha-resumo acima do seu detalhe.
    Devolve a quantidade de subgrupos "Consolidado - {órgão}" criados."""
    r = 2
    n_org_subgroups = 0
    for _code_full, block in code_blocks:
        n = len(block)
        if _is_subtotal_label(block[0][1], prefix='Consolidado'):
            n_org_subgroups += _apply_breakdown_outline(ws, r, block)
        else:
            orgs_seen: list[CellValue] = []
            for offset in range(n):
                orgao_val = block[offset][6]
                row_i = r + offset
                if orgao_val not in orgs_seen:
                    orgs_seen.append(orgao_val)
                    level = 0 if offset == 0 else 1
                    ws.row_dimensions[row_i].outlineLevel = level
                    ws.row_dimensions[row_i].hidden = level != 0
                    if level == 0:
                        ws.row_dimensions[row_i].collapsed = len(orgs_seen) < n
                    n_org_subgroups += 1
                else:
                    ws.row_dimensions[row_i].outlineLevel = 2
                    ws.row_dimensions[row_i].hidden = True
        r += n
    return n_org_subgroups
