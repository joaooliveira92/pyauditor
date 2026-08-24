"""Aba "Prazos" de `sintetico.xlsx`: tabela de referência de SLA formatada,
com criticidade colorida (nunca só pela cor — o texto permanece sempre
visível) e duplicidades de Demanda/Criticidade sinalizadas. Título/subtítulo
compartilhados com a Capa (`=Capa!B2`, nunca redigitado).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

from openpyxl import Workbook

from pyauditor.excel._style import (
    BODY_FONT,
    CENTER_ALIGN,
    CRITICIDADE_FILL_BY_VALUE,
    HEADER_FILL,
    HEADER_FONT,
    LABEL_FONT,
    LEFT_ALIGN,
    LEFT_WRAP_ALIGN,
    SECTION_FONT,
    SUBTITLE_FONT,
    THIN_BORDER,
    TITLE_FONT,
    TOP_WRAP_ALIGN,
    setup_institutional_print,
)
from pyauditor.excel.prazos import PRAZOS_SHEET_NAME, read_prazos
from pyauditor.excel.sintetico._sheets._shared import (
    flag_pendencia,
    wrapped_row_height,
)

_TITLE: Final[str] = (
    'DEMONSTRATIVO DE EXECUÇÃO DOS SERVIÇOS DE INFRAESTRUTURA DE TI'
)
_SUBTITLE_REF_FORMULA: Final[str] = '=Capa!B2'

_ROW_TITLE: Final[int] = 1
_ROW_SUBTITLE: Final[int] = 2
_ROW_SECTION: Final[int] = 4

_PRAZO_HORAS_RE: Final = re.compile(
    r'^\s*(\d+)\s*h\s*\(horas corridas\)\s*$', re.IGNORECASE
)
# Nota partida em duas linhas (uma frase por linha) — layout atual da aba.
_PRAZOS_NOTE_LINES: Final[tuple[str, str]] = (
    'Os prazos abaixo constituem parâmetros contratuais de referência. ',
    'Eventuais pausas, suspensões ou regras especiais de contagem devem '
    'estar amparadas pelo instrumento contratual ou por evidência formal.',
)
_ROW_PRAZOS_NOTE_1: Final[int] = 5
_ROW_PRAZOS_NOTE_2: Final[int] = 6
_ROW_PRAZOS_HEADER: Final[int] = 8
_ROW_PRAZOS_BODY_START: Final[int] = 9


def _reformat_prazo_text(value: str) -> str:
    """'2h (horas corridas)' → '2 horas corridas' (spec §5.5); demais textos
    (ex. a regra de Projetos) ficam como estão — não há forma redundante a
    padronizar."""
    match = _PRAZO_HORAS_RE.match(value)
    if match is None:
        return value
    return f'{match.group(1)} horas corridas'


def _reformat_criticidade(value: str) -> str:
    """'-' é ambíguo (spec §5.5) — vira 'Não aplicável' (usado por Projetos)."""
    stripped = value.strip()
    return 'Não aplicável' if stripped == '-' else stripped


def write_prazos_sheet(
    workbook: Workbook,
    prazos_path: Path,
    contract_number: str | None,
    warnings: list[str],
) -> None:
    """Aba "Prazos": tabela de referência de SLA formatada, com criticidade
    colorida (nunca só pela cor — o texto permanece sempre visível) e
    duplicidades de Demanda/Criticidade sinalizadas."""
    try:
        header, rows = read_prazos(prazos_path)
    except FileNotFoundError:
        warnings.append(
            f'sintetico.xlsx: {prazos_path} não encontrado — aba '
            f"'{PRAZOS_SHEET_NAME}' não gerada"
        )
        return
    except (OSError, ValueError) as exc:
        warnings.append(
            f'sintetico.xlsx: falha ao ler {prazos_path}: {exc} — aba '
            f"'{PRAZOS_SHEET_NAME}' não gerada"
        )
        return

    sheet = workbook.create_sheet(title=PRAZOS_SHEET_NAME)
    sheet.sheet_view.showGridLines = False
    sheet.column_dimensions['A'].width = 5
    sheet.column_dimensions['B'].width = 14.33
    sheet.column_dimensions['C'].width = 12.66
    sheet.column_dimensions['D'].width = 32.83

    sheet.cell(row=_ROW_TITLE, column=2, value=_TITLE).font = TITLE_FONT
    sheet.row_dimensions[_ROW_TITLE].height = 18
    sheet.cell(
        row=_ROW_SUBTITLE, column=2, value=_SUBTITLE_REF_FORMULA
    ).font = SUBTITLE_FONT

    sheet.merge_cells(
        start_row=_ROW_SECTION,
        start_column=2,
        end_row=_ROW_SECTION,
        end_column=4,
    )
    sheet.cell(
        row=_ROW_SECTION, column=2, value='PRAZOS MÁXIMOS PARA ATENDIMENTO'
    ).font = SECTION_FONT
    sheet.row_dimensions[_ROW_SECTION].height = 16

    note_width = 14.33 + 12.66 + 32.83
    for note_row, sentence in zip(
        (_ROW_PRAZOS_NOTE_1, _ROW_PRAZOS_NOTE_2),
        _PRAZOS_NOTE_LINES,
        strict=True,
    ):
        sheet.merge_cells(
            start_row=note_row, start_column=2, end_row=note_row, end_column=4
        )
        note_cell = sheet.cell(row=note_row, column=2, value=sentence)
        note_cell.font = BODY_FONT
        note_cell.alignment = TOP_WRAP_ALIGN
        note_height = wrapped_row_height(sentence, note_width)
        if note_height is not None:
            sheet.row_dimensions[note_row].height = note_height

    header_labels = (
        tuple(header[:3])
        if len(header) >= 3
        else (
            'Demanda',
            'Criticidade',
            'Prazo máximo para atendimento',
        )
    )
    header_row = _ROW_PRAZOS_HEADER
    for column, label in zip((2, 3, 4), header_labels, strict=True):
        cell = sheet.cell(row=header_row, column=column, value=label)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = CENTER_ALIGN if column == 3 else LEFT_ALIGN

    seen_combos: set[tuple[str, str]] = set()
    row = _ROW_PRAZOS_BODY_START
    for data_row in rows:
        padded = list(data_row) + [''] * (3 - len(data_row))
        demanda = padded[0].strip()
        criticidade = _reformat_criticidade(padded[1])
        prazo = _reformat_prazo_text(padded[2].strip())

        demanda_cell = sheet.cell(row=row, column=2, value=demanda)
        demanda_cell.font = LABEL_FONT
        demanda_cell.alignment = LEFT_ALIGN
        demanda_cell.border = THIN_BORDER

        combo = (demanda, criticidade)
        if combo in seen_combos:
            flag_pendencia(
                demanda_cell,
                f'Combinação duplicada: {demanda!r} / {criticidade!r}.',
            )
        else:
            seen_combos.add(combo)

        criticidade_cell = sheet.cell(row=row, column=3, value=criticidade)
        criticidade_cell.font = BODY_FONT
        criticidade_cell.alignment = CENTER_ALIGN
        criticidade_cell.border = THIN_BORDER
        fill = CRITICIDADE_FILL_BY_VALUE.get(criticidade)
        if fill is not None:
            criticidade_cell.fill = fill

        prazo_cell = sheet.cell(row=row, column=4, value=prazo)
        prazo_cell.font = BODY_FONT
        prazo_cell.alignment = LEFT_WRAP_ALIGN
        prazo_cell.border = THIN_BORDER
        prazo_height = wrapped_row_height(prazo, 32.83)
        if prazo_height is not None:
            sheet.row_dimensions[row].height = prazo_height
        row += 1

    last_row = row - 1
    setup_institutional_print(
        sheet,
        contract_number=contract_number,
        last_row=last_row,
        last_column=4,
        header_row=header_row,
        first_column=2,
    )
