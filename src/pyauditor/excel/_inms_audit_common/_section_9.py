"""Seção 9 (penalidade, ratio único com `base_points`) — compartilhada
entre as abas enriquecidas de INMS cujo cálculo é um único ratio (INMS 1.1,
INMS 1.3); extraída de `excel/inms_1_1/_sections_8_9.py` quando o INMS 1.3
ganhou seu próprio renderer enriquecido. Não se aplica ao INMS 1.2
(`segmented_ratio`, sem `base_points`, um sub-cálculo por categoria) — ver
`excel/inms_1_2/_section_9.py`.
"""

from __future__ import annotations

from openpyxl.styles import Alignment, Font
from openpyxl.worksheet.worksheet import Worksheet

from pyauditor.excel._inms_audit_common._cells import (
    label_value,
    section_bar,
)
from pyauditor.excel._inms_audit_common._layout import (
    NOTE_FONT,
    ORANGE_FILL,
    PCT4,
    TEAL_FILL,
)


def write_section_9_penalidade_ratio(
    sheet: Worksheet,
    *,
    penalty_base_points: float,
    penalty_step_points: float,
    penalty_step_size_pct: float,
    start_row: int,
) -> None:
    s9_bar = start_row
    section_bar(
        sheet, s9_bar, 'SEÇÃO 9 · PENALIDADE (CÁLCULO PRELIMINAR)', last_col=6
    )
    label_value(sheet, s9_bar + 1, 'Meta:', '=A13', fmt=PCT4)
    label_value(sheet, s9_bar + 2, 'Resultado:', '=E13', fmt=PCT4)
    diff9_row = s9_bar + 3
    # Meta mínima ("`>=`") — único operador suportado por este renderer.
    diff_formula = '=IF(B13=0,"",A13-E13)'
    label_value(
        sheet,
        diff9_row,
        'Diferença (Meta - Resultado):',
        diff_formula,
        fmt=PCT4,
    )
    diffpp_row = diff9_row + 1
    label_value(
        sheet,
        diffpp_row,
        'Diferença em pontos percentuais:',
        f'=IF(B{diff9_row}="","",B{diff9_row}*100)',
        fmt='0.0000',
    )
    base_row = diffpp_row + 1
    below_target = 'E13<A13'
    label_value(
        sheet,
        base_row,
        'Penalidade-base:',
        f'=IF(B13=0,"Não '
        f'aplicável",IF({below_target},{penalty_base_points:g},0))',
        fmt='0',
    )
    add_row = base_row + 1
    label_value(
        sheet,
        add_row,
        f'Adicional proporcional ({penalty_step_points:g} pontos a cada '
        f'{penalty_step_size_pct:g} p.p. — cálculo contínuo):',
        (
            f'=IF(B13=0,"Não aplicável",IF({below_target},'
            f'(B{diffpp_row}/{penalty_step_size_pct!r})*{penalty_step_points!r},0))'
        ),
        fmt='0.0000',
    )
    total_row = add_row + 1
    label_value(
        sheet,
        total_row,
        'Total proporcional (base + adicional):',
        (
            f'=IF(OR(ISTEXT(B{base_row}),ISTEXT(B{add_row})),"Não '
            f'aplicável",B{base_row}+B{add_row})'
        ),
        fmt='0.0000',
        fill=TEAL_FILL,
    )
    scenario_row = total_row + 1
    label_value(
        sheet,
        scenario_row,
        'Cenário — faixas completas ou iniciadas:',
        (
            f'=IF(B13=0,"Não '
            f'aplicável",IF({below_target},{penalty_base_points:g}+'
            f'CEILING(B{diffpp_row},{penalty_step_size_pct!r})/{penalty_step_size_pct!r}'
            f'*{penalty_step_points!r},0))'
        ),
        fmt='0',
        fill=ORANGE_FILL,
    )
    obs_row = scenario_row + 2
    sheet.merge_cells(f'A{obs_row}:L{obs_row}')
    sheet[f'A{obs_row}'] = (
        'Resultado sujeito à confirmação da regra de arredondamento e das '
        'disposições '
        'gerais de glosa do Termo de Referência.'
    )
    sheet[f'A{obs_row}'].font = Font(
        name='Arial', size=10, bold=True, color='9A3412'
    )
    sheet[f'A{obs_row}'].fill = ORANGE_FILL
    sheet[f'A{obs_row}'].alignment = Alignment(wrap_text=True)

    final_note_row = obs_row + 2
    sheet.merge_cells(f'A{final_note_row}:L{final_note_row}')
    sheet[f'A{final_note_row}'] = (
        'Dados de apoio às fórmulas desta aba nas colunas R:AM (estrutura de '
        'apoio, '
        'auditável) — mantidos para rastreabilidade; não excluir nem reordenar.'
    )
    sheet[f'A{final_note_row}'].font = NOTE_FONT
