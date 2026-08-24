"""Aba "Equipe" de `sintetico.xlsx`: título/subtítulo compartilhados com a
Capa (subtítulo via fórmula `=Capa!B2`, nunca redigitado) + tabela de gestão
e fiscalização (FUNÇÃO/NOME/SIAPE) + seção de perfis profissionais lida de
`perfis_profissionais.csv`. Pendências são sinalizadas por célula, nunca
corrigidas automaticamente (SIAPE ausente/fora do padrão, duplicidades).
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Final

from openpyxl import Workbook
from openpyxl.styles import Alignment
from openpyxl.worksheet.worksheet import Worksheet

from pyauditor.excel._style import (
    BODY_FONT,
    CENTER_ALIGN,
    HEADER_FILL,
    HEADER_FONT,
    LEFT_ALIGN,
    LEFT_WRAP_ALIGN,
    SECTION_FONT,
    SUBSTITUTO_FILL,
    SUBTITLE_FONT,
    THIN_BORDER,
    TITLE_FONT,
    setup_institutional_print,
)
from pyauditor.excel.equipe import EQUIPE_DELIMITER, EQUIPE_ENCODING
from pyauditor.excel.perfis_profissionais import (
    CATEGORIA_HEADER,
    CBO_HEADER,
    DENOMINACAO_HEADER,
    N_ITEM_HEADER,
    PRESENCIAL_HEADER,
    QUANTIDADE_HEADER,
    QUANTIDADE_TOTAL_HEADER,
    read_perfis_profissionais,
)
from pyauditor.excel.sintetico._sheets._shared import (
    EQUIPE_SHEET_NAME,
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
_ROW_HEADER: Final[int] = 6
_ROW_BODY_START: Final[int] = 7

_SUBSTITUTO_RE: Final = re.compile(r'\s*-?\s*substituto$', re.IGNORECASE)


def _normalize_funcao_display(funcao: str) -> tuple[str, bool]:
    """Convenção única do hífen (spec §4.4): 'X Substituto'/'X - Substituto'
    ambos viram 'X - Substituto'."""
    match = _SUBSTITUTO_RE.search(funcao)
    if match is None:
        return funcao, False
    base = funcao[: match.start()].rstrip()
    return f'{base} - Substituto', True


def write_equipe_sheet(
    workbook: Workbook,
    equipe_path: Path,
    perfis_profissionais_path: Path | None,
    contract_number: str | None,
    warnings: list[str],
) -> None:
    """Aba "Equipe": título/subtítulo compartilhados com a Capa (subtítulo
    via fórmula `=Capa!B2`, nunca redigitado) + tabela de gestão e
    fiscalização (FUNÇÃO/NOME/SIAPE, com merges B:C na função e D:F no nome)
    + seção de perfis profissionais lida de `perfis_profissionais.csv`
    (quando o arquivo é dado). Pendências são sinalizadas por célula, nunca
    corrigidas automaticamente (SIAPE ausente/fora do padrão, duplicidades)."""
    try:
        with equipe_path.open(encoding=EQUIPE_ENCODING, newline='') as handle:
            rows = list(csv.DictReader(handle, delimiter=EQUIPE_DELIMITER))
    except FileNotFoundError:
        warnings.append(
            f'sintetico.xlsx: {equipe_path} não encontrado — aba '
            f"'{EQUIPE_SHEET_NAME}' não gerada"
        )
        return
    except OSError as exc:
        warnings.append(
            f'sintetico.xlsx: falha ao ler {equipe_path}: {exc} — aba '
            f"'{EQUIPE_SHEET_NAME}' não gerada"
        )
        return

    sheet = workbook.create_sheet(title=EQUIPE_SHEET_NAME)
    sheet.sheet_view.showGridLines = False
    sheet.column_dimensions['A'].width = 5
    sheet.column_dimensions['B'].width = 6.5
    sheet.column_dimensions['C'].width = 44.5
    sheet.column_dimensions['D'].width = 12.8
    sheet.column_dimensions['E'].width = 17.8
    sheet.column_dimensions['F'].width = 38.3
    sheet.column_dimensions['G'].width = 17.3
    sheet.column_dimensions['I'].width = 36.7

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
        row=_ROW_SECTION,
        column=2,
        value='EQUIPE DE GESTÃO E FISCALIZAÇÃO DO CONTRATO',
    ).font = SECTION_FONT
    sheet.row_dimensions[_ROW_SECTION].height = 16

    header_row = _ROW_HEADER
    # Coluna B (função) e D (nome) levam merges: a função ocupa B:C e o nome
    # D:F; o SIAPE fica na coluna G. Os cabeçalhos são centralizados.
    for column in (2, 4, 7):
        cell = sheet.cell(row=header_row, column=column)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = CENTER_ALIGN
    sheet.cell(row=header_row, column=2, value='FUNÇÃO')
    sheet.cell(row=header_row, column=4, value='NOME')
    sheet.cell(row=header_row, column=7, value='SIAPE')
    for column in (2, 4):
        sheet.merge_cells(
            start_row=header_row,
            start_column=column,
            end_row=header_row,
            end_column=column + 1 if column == 2 else column + 2,
        )

    seen_funcoes: set[str] = set()
    seen_siapes: set[str] = set()
    row = _ROW_BODY_START
    for entry in rows:
        funcao_raw = (entry.get('FUNÇÃO') or '').strip()
        nome = (entry.get('NOME') or '').strip()
        siape = (entry.get('SIAPE') or '').strip()
        if not funcao_raw and not nome and not siape:
            continue

        funcao_display, eh_substituto = _normalize_funcao_display(funcao_raw)

        sheet.merge_cells(
            start_row=row, start_column=2, end_row=row, end_column=3
        )
        sheet.merge_cells(
            start_row=row, start_column=4, end_row=row, end_column=6
        )
        funcao_cell = sheet.cell(row=row, column=2, value=funcao_display)
        nome_cell = sheet.cell(row=row, column=4, value=nome)
        siape_cell = sheet.cell(row=row, column=7, value=siape)

        funcao_cell.font = BODY_FONT
        funcao_cell.alignment = LEFT_WRAP_ALIGN
        funcao_cell.border = THIN_BORDER
        nome_cell.font = BODY_FONT
        nome_cell.alignment = LEFT_WRAP_ALIGN
        nome_cell.border = THIN_BORDER
        siape_cell.font = BODY_FONT
        siape_cell.alignment = CENTER_ALIGN
        siape_cell.border = THIN_BORDER
        siape_cell.number_format = '@'
        nome_height = wrapped_row_height(nome, 68.9)
        if nome_height is not None:
            sheet.row_dimensions[row].height = nome_height

        if eh_substituto:
            funcao_cell.fill = SUBSTITUTO_FILL
            nome_cell.fill = SUBSTITUTO_FILL
            siape_cell.fill = SUBSTITUTO_FILL

        if not funcao_raw:
            flag_pendencia(funcao_cell, 'Função ausente.')
        elif funcao_display in seen_funcoes:
            flag_pendencia(
                funcao_cell, f'Função duplicada: {funcao_display!r}.'
            )
        else:
            seen_funcoes.add(funcao_display)

        if not nome:
            flag_pendencia(nome_cell, 'Nome ausente.')

        if not siape:
            flag_pendencia(siape_cell, 'SIAPE ausente.')
        elif not (siape.isdigit() and len(siape) == 7):
            flag_pendencia(
                siape_cell, f'SIAPE fora do padrão de 7 dígitos: {siape!r}.'
            )
        elif siape in seen_siapes:
            flag_pendencia(siape_cell, f'SIAPE duplicado: {siape!r}.')
        else:
            seen_siapes.add(siape)

        row += 1

    last_gestao_row = row - 1

    if perfis_profissionais_path is not None:
        last_row = _write_perfis_profissionais_section(
            sheet, last_gestao_row, perfis_profissionais_path, warnings
        )
        last_column = 9
    else:
        last_row = last_gestao_row
        last_column = 4

    setup_institutional_print(
        sheet,
        contract_number=contract_number,
        last_row=last_row,
        last_column=last_column,
        header_row=header_row,
        first_column=2,
    )


def _write_perfis_profissionais_section(
    sheet: Worksheet,
    last_gestao_row: int,
    path: Path,
    warnings: list[str],
) -> int:
    """Seção de perfis profissionais da aba Equipe (abaixo da tabela de
    gestão/fiscalização), lida de `perfis_profissionais.csv`: título da
    seção, cabeçalho ITEM/CATEGORIA/QUANTIDADE/CBO/DENOMINAÇÃO/QUANTIDADE/
    PRESENCIAL-REMOTO, uma linha por perfil (zebra alternada) e totais de
    quantidade por fórmula. Devolve a última linha escrita (para a área de
    impressão); devolve `last_gestao_row` quando o arquivo está ausente/em
    branco."""
    try:
        perfis = read_perfis_profissionais(path)
    except FileNotFoundError:
        warnings.append(
            f'sintetico.xlsx: {path} não encontrado — seção de perfis '
            f"profissionais não anexada à aba '{EQUIPE_SHEET_NAME}'"
        )
        return last_gestao_row
    except (OSError, ValueError) as exc:
        warnings.append(
            f'sintetico.xlsx: falha ao ler {path}: {exc} — seção de perfis '
            f"profissionais não anexada à aba '{EQUIPE_SHEET_NAME}'"
        )
        return last_gestao_row

    if not perfis:
        return last_gestao_row

    # Layout da edição: 3 linhas em branco após a tabela de gestão, título da
    # seção (mesmo texto da seção superior), 1 branco, cabeçalho, corpo.
    title_row = last_gestao_row + 4
    header_row = title_row + 2
    body_start = header_row + 1

    sheet.merge_cells(
        start_row=title_row, start_column=2, end_row=title_row, end_column=4
    )
    title_cell = sheet.cell(
        row=title_row,
        column=2,
        value='PERFIS PROFISSIONAIS',
    )
    title_cell.font = SECTION_FONT
    sheet.row_dimensions[title_row].height = 16

    headers: tuple[tuple[int, str], ...] = (
        (2, 'ITEM'),
        (3, 'CATEGORIA'),
        (4, 'QUANTIDADE'),
        (5, 'CBO'),
        (6, 'DENOMINAÇÃO DO PERFIL'),
        (8, 'QUANTIDADE'),
        (9, 'PRESENCIAL/REMOTO'),
    )
    for column, label in headers:
        cell = sheet.cell(row=header_row, column=column, value=label)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = CENTER_ALIGN if column in (4, 8, 9) else LEFT_ALIGN

    def _as_int(raw: str) -> int | str:
        """QUANTIDADE/ITEM do CSV vêm como texto; vira int quando numérico,
        senão preserva o texto — a fórmula `SUM` do total precisa de números."""
        try:
            return int(raw)
        except ValueError:
            return raw

    row = body_start
    for index, perfil in enumerate(perfis):
        row_fill = SUBSTITUTO_FILL if index % 2 == 1 else None

        item_cell = sheet.cell(
            row=row, column=2, value=_as_int(perfil[N_ITEM_HEADER])
        )
        item_cell.font = BODY_FONT
        item_cell.alignment = Alignment(horizontal='right', vertical='center')
        item_cell.border = THIN_BORDER

        categoria_cell = sheet.cell(
            row=row, column=3, value=perfil[CATEGORIA_HEADER]
        )
        categoria_cell.font = BODY_FONT
        categoria_cell.alignment = LEFT_WRAP_ALIGN
        categoria_cell.border = THIN_BORDER

        quantidade_total_cell = sheet.cell(
            row=row,
            column=4,
            value=_as_int(perfil[QUANTIDADE_TOTAL_HEADER]),
        )
        quantidade_total_cell.font = BODY_FONT
        quantidade_total_cell.alignment = CENTER_ALIGN
        quantidade_total_cell.border = THIN_BORDER
        quantidade_total_cell.number_format = '@'

        cbo_cell = sheet.cell(row=row, column=5, value=perfil[CBO_HEADER])
        cbo_cell.font = BODY_FONT
        cbo_cell.alignment = LEFT_ALIGN
        cbo_cell.border = THIN_BORDER

        sheet.merge_cells(
            start_row=row, start_column=6, end_row=row, end_column=7
        )
        denominacao_cell = sheet.cell(
            row=row, column=6, value=perfil[DENOMINACAO_HEADER]
        )
        denominacao_cell.font = BODY_FONT
        denominacao_cell.alignment = LEFT_WRAP_ALIGN
        denominacao_cell.border = THIN_BORDER

        quantidade_cell = sheet.cell(
            row=row, column=8, value=_as_int(perfil[QUANTIDADE_HEADER])
        )
        quantidade_cell.font = BODY_FONT
        quantidade_cell.alignment = CENTER_ALIGN
        quantidade_cell.border = THIN_BORDER
        quantidade_cell.number_format = '@'

        presencial_cell = sheet.cell(
            row=row, column=9, value=perfil[PRESENCIAL_HEADER]
        )
        presencial_cell.font = BODY_FONT
        presencial_cell.alignment = LEFT_ALIGN
        presencial_cell.border = THIN_BORDER
        presencial_cell.number_format = '@'

        for cell in (
            item_cell,
            categoria_cell,
            quantidade_total_cell,
            cbo_cell,
            denominacao_cell,
            quantidade_cell,
            presencial_cell,
        ):
            if row_fill is not None:
                cell.fill = row_fill

        row += 1

    total_row = row
    total_qtd_cell = sheet.cell(
        row=total_row,
        column=4,
        value=f'=SUM(D{body_start}:D{row - 1})',
    )
    total_qtd_cell.number_format = '@'
    total_qtd_cell.alignment = CENTER_ALIGN
    total_qtd_cell.font = BODY_FONT
    total_perfil_cell = sheet.cell(
        row=total_row,
        column=8,
        value=f'=SUM(H{body_start}:H{row - 1})',
    )
    total_perfil_cell.number_format = '@'
    total_perfil_cell.alignment = CENTER_ALIGN
    total_perfil_cell.font = BODY_FONT

    return total_row
