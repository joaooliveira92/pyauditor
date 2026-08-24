"""Aba "Capa" de `sintetico.xlsx`: título/subtítulo do documento + seção
"INFORMAÇÕES INICIAIS" (identificação contratual, com vigência calculada por
fórmula a partir das datas reais) + bloco complementar "Dados Contratuais"
(`dados_contratuais.yaml`, colunas F/G) + seção de itens/valores
(`objetos.csv`). Preserva os valores originais (nunca inventa nem corrige
dado contratual); sinaliza pendências (preenchimento amarelo-claro +
comentário) em vez de corrigir automaticamente.
"""

from __future__ import annotations

import csv
import re
from datetime import datetime
from pathlib import Path
from typing import Final, cast

from openpyxl import Workbook
from openpyxl.cell.cell import Cell
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from pyauditor.excel._style import (
    BODY_FONT,
    CENTER_ALIGN,
    HEADER_FILL,
    HEADER_FONT,
    LABEL_FONT,
    LEFT_ALIGN,
    LEFT_WRAP_ALIGN,
    SECTION_FONT,
    SUBSTITUTO_FILL,
    SUBTITLE_FONT,
    THIN_BORDER,
    TITLE_FONT,
    setup_institutional_print,
)
from pyauditor.excel.capa import read_capa_csv_fields
from pyauditor.excel.dados_contratuais import read_dados_contratuais_fields
from pyauditor.excel.objetos import (
    OBJETOS_DELIMITER,
    OBJETOS_ENCODING,
    parse_brl_value,
)
from pyauditor.excel.sintetico._sheets._shared import (
    CAPA_SHEET_NAME,
    CapaContext,
    flag_pendencia,
    wrapped_row_height,
)

_TITLE: Final[str] = (
    'DEMONSTRATIVO DE EXECUÇÃO DOS SERVIÇOS DE INFRAESTRUTURA DE TI'
)
_SECTION_TITLE: Final[str] = 'INFORMAÇÕES INICIAIS'

# Esqueleto de linhas: título do documento, subtítulo (fórmula dinâmica),
# branco, título da seção, branco, cabeçalho da tabela, corpo.
_ROW_TITLE: Final[int] = 1
_ROW_SUBTITLE: Final[int] = 2
_ROW_SECTION: Final[int] = 4
_ROW_HEADER: Final[int] = 6
_ROW_BODY_START: Final[int] = 7

# Coluna B/C/D da Seção "INFORMAÇÕES INICIAIS" (identificação contratual).
# "Contrato" é um campo comum do CSV (como os demais) — existe para a
# fórmula do subtítulo (B2) referenciar uma célula em vez de redigitar o
# número do contrato. "Vigência Contratual"/"Vigência Restante" são
# sintéticos: "Vigência" (texto livre tipo "12 meses") sai da exibição,
# substituída por duas contagens calculadas a partir das datas reais.
_IDENTIFICACAO_LABELS: Final[tuple[str, ...]] = (
    'Número do contrato',
    'Processo SEI',
    'Empresa contratada',
    'CNPJ da contratada',
    'Contrato',
    'Objeto',
    'Termo Aditivo 1',
    'Termo Aditivo 2',
    'Termo Aditivo 3',
    'Portaria Equipe',
    'Vigência Contratual',
    'Vigência Restante',
    'Início da vigência',
    'Término da vigência',
)
_SINTETICOS_VIGENCIA: Final[frozenset[str]] = frozenset(
    {'Vigência Contratual', 'Vigência Restante'}
)
# Bloco "Dados Contratuais" (parâmetros contratuais complementares lidos de
# `input/dados_contratuais.yaml`): colunas F (Campo) e G (Valor), alinhadas
# ao mesmo cabeçalho do bloco B:D — uma linha por par campo/valor do YAML, na
# ordem do arquivo, sem mescla (a coluna F é o rótulo e a G o valor).
_DADOS_CONTRATUAIS_LABEL_COL: Final[int] = 6
_DADOS_CONTRATUAIS_VALUE_COL: Final[int] = 7
_DADOS_CONTRATUAIS_LABEL_WIDTH: Final[float] = 40.5
_DADOS_CONTRATUAIS_VALUE_WIDTH: Final[float] = 50.16
_DATE_LABELS: Final[frozenset[str]] = frozenset(
    {'Início da vigência', 'Término da vigência'}
)
_WRAP_LABELS: Final[frozenset[str]] = frozenset(
    {'Objeto', 'Empresa contratada'}
)
_TEXT_LABELS: Final[frozenset[str]] = frozenset(
    {
        'Número do contrato',
        'Processo SEI',
        'CNPJ da contratada',
        'Contrato',
        'Termo Aditivo 1',
        'Termo Aditivo 2',
        'Termo Aditivo 3',
    }
)

_CATEGORIA_PENDENCIA: Final[str] = 'Aplicações. virtualização'
_CATEGORIA_PENDENCIA_MSG: Final[str] = (
    'Possível erro de pontuação/capitalização ("Aplicações e Virtualização"?)'
    ' — denominação possivelmente contratual, não corrigida automaticamente.'
)


def _strip_fields(raw: dict[str, str]) -> dict[str, str]:
    return {label: value.strip() for label, value in raw.items()}


def _parse_data_br(value: str) -> datetime | None:
    try:
        return datetime.strptime(value, '%d/%m/%Y')
    except ValueError:
        return None


def _only_digits(value: str) -> str:
    return re.sub(r'\D', '', value)


def _rendered_identificacao_labels(
    raw_fields: dict[str, str],
) -> list[str]:
    """Filtra `_IDENTIFICACAO_LABELS` aos rótulos que de fato aparecem —
    campos ausentes no CSV somem; os sintéticos só entram quando o campo do
    qual dependem está presente (e, no caso das vigências, com datas
    válidas: sem datas reais não há como montar a fórmula)."""
    inicio_valido = (
        _parse_data_br(raw_fields.get('Início da vigência', '')) is not None
    )
    termino_valido = (
        _parse_data_br(raw_fields.get('Término da vigência', '')) is not None
    )

    rendered: list[str] = []
    for label in _IDENTIFICACAO_LABELS:
        if label in _SINTETICOS_VIGENCIA:
            if inicio_valido and termino_valido:
                rendered.append(label)
        elif label in raw_fields:
            rendered.append(label)
    return rendered


def write_capa_sheet(
    workbook: Workbook,
    capa_path: Path,
    dados_contratuais_path: Path | None,
    objetos_path: Path | None,
    warnings: list[str],
) -> CapaContext:
    """Aba "Capa": título/subtítulo do documento + seção "INFORMAÇÕES
    INICIAIS" (identificação contratual, com vigência calculada por fórmula
    a partir das datas reais) + itens/valores. Quando
    `dados_contratuais_path` é dado, um bloco complementar de parâmetros
    contratuais (Fator-K, valor global, garantias, limites, prazos) é
    anexado nas colunas F/G, alinhado ao mesmo cabeçalho. Devolve o número
    do contrato, que Equipe/Prazos usam só no rodapé — título/subtítulo
    delas referenciam esta aba diretamente via fórmula, nunca por segunda
    digitação."""
    try:
        raw_fields = _strip_fields(read_capa_csv_fields(capa_path))
    except FileNotFoundError:
        warnings.append(
            f'sintetico.xlsx: {capa_path} não encontrado — aba '
            f"'{CAPA_SHEET_NAME}' não gerada"
        )
        return CapaContext(None)
    except (OSError, ValueError) as exc:
        warnings.append(
            f'sintetico.xlsx: falha ao ler {capa_path}: {exc} — aba '
            f"'{CAPA_SHEET_NAME}' não gerada"
        )
        return CapaContext(None)

    numero_contrato = raw_fields.get('Número do contrato') or None

    sheet = workbook.create_sheet(title=CAPA_SHEET_NAME)
    sheet.sheet_view.showGridLines = False
    # Coluna A é só recuo visual — o conteúdo começa em B (rótulo, mesclado
    # B:C) e o valor fica em D.
    sheet.column_dimensions['A'].width = 5
    sheet.column_dimensions['B'].width = 14.33
    sheet.column_dimensions['C'].width = 29.66
    sheet.column_dimensions['D'].width = 31.0

    sheet.cell(row=_ROW_TITLE, column=2, value=_TITLE).font = TITLE_FONT
    sheet.row_dimensions[_ROW_TITLE].height = 18

    rendered_labels = _rendered_identificacao_labels(raw_fields)
    row_by_label = {
        label: _ROW_BODY_START + i for i, label in enumerate(rendered_labels)
    }

    if 'Contrato' in row_by_label:
        subtitulo = f'=_xlfn.CONCAT("Contrato nº",D{row_by_label["Contrato"]})'
    else:
        subtitulo = f'Contrato nº {numero_contrato}' if numero_contrato else ''
    sheet.cell(
        row=_ROW_SUBTITLE, column=2, value=subtitulo
    ).font = SUBTITLE_FONT
    hoje_cell = sheet.cell(row=_ROW_SUBTITLE, column=4, value='=TODAY()')
    hoje_cell.font = BODY_FONT
    hoje_cell.number_format = 'dd/mm/yyyy'

    sheet.merge_cells(
        start_row=_ROW_SECTION,
        start_column=2,
        end_row=_ROW_SECTION,
        end_column=4,
    )
    sheet.cell(
        row=_ROW_SECTION, column=2, value=_SECTION_TITLE
    ).font = SECTION_FONT
    sheet.row_dimensions[_ROW_SECTION].height = 16

    sheet.cell(row=_ROW_HEADER, column=2, value='Campo').font = HEADER_FONT
    sheet.cell(row=_ROW_HEADER, column=2).fill = HEADER_FILL
    sheet.cell(row=_ROW_HEADER, column=3).fill = HEADER_FILL
    sheet.cell(row=_ROW_HEADER, column=4, value='Valor').font = HEADER_FONT
    sheet.cell(row=_ROW_HEADER, column=4).fill = HEADER_FILL

    inicio_dt: datetime | None = None
    termino_dt: datetime | None = None

    if dados_contratuais_path is not None:
        _write_dados_contratuais_block(sheet, dados_contratuais_path, warnings)

    row = _ROW_BODY_START
    for index, label in enumerate(rendered_labels):
        value = raw_fields.get(label, '')
        # Zebra igual à Equipe (lá, a cor marca substitutos; aqui é só
        # listras alternadas, não há linhas com esse status).
        row_fill = SUBSTITUTO_FILL if index % 2 == 1 else None

        sheet.merge_cells(
            start_row=row, start_column=2, end_row=row, end_column=3
        )
        label_cell = sheet.cell(row=row, column=2, value=label)
        # Estilo alinhado ao da Equipe: os rótulos do corpo não são negrito —
        # só o cabeçalho ('Campo'/'Valor') leva o destaque.
        label_cell.font = BODY_FONT
        label_cell.alignment = LEFT_ALIGN
        label_cell.border = THIN_BORDER
        if row_fill is not None:
            label_cell.fill = row_fill
        # A célula fusionada B:C só estiliza sua âncora (B); sem isto, a
        # borda direita da região fusionada não se cerra (fica a cargo da
        # célula 'Valor' em D). Aplicar borda/preenchimento também a C fecha
        # o perímetro da célula 'Campo'.
        merged_label_cell = cast(Cell, sheet.cell(row=row, column=3))
        merged_label_cell.border = THIN_BORDER
        if row_fill is not None:
            merged_label_cell.fill = row_fill

        value_cell = cast(Cell, sheet.cell(row=row, column=4))
        value_cell.font = BODY_FONT
        value_cell.border = THIN_BORDER
        if row_fill is not None:
            value_cell.fill = row_fill

        if label in _SINTETICOS_VIGENCIA:
            inicio_ref = f'D{row_by_label["Início da vigência"]}'
            termino_ref = f'D{row_by_label["Término da vigência"]}'
            if label == 'Vigência Contratual':
                formula = (
                    f'=_xlfn.CONCAT(DATEDIF({inicio_ref},{termino_ref},"D"),'
                    f' " dias")'
                )
            else:
                formula = (
                    f'=_xlfn.CONCAT(DATEDIF(TODAY(),{termino_ref},"D"),'
                    f' " dias")'
                )
            value_cell.value = formula
            value_cell.alignment = LEFT_ALIGN
        elif label in _DATE_LABELS:
            parsed = _parse_data_br(value)
            if parsed is not None:
                value_cell.value = parsed
                value_cell.number_format = 'dd/mm/yyyy'
                value_cell.alignment = CENTER_ALIGN
                if label == 'Início da vigência':
                    inicio_dt = parsed
                else:
                    termino_dt = parsed
            else:
                value_cell.value = value
                value_cell.alignment = LEFT_ALIGN
                if value:
                    flag_pendencia(
                        value_cell,
                        f'Data em formato inesperado (esperado dd/mm/aaaa): '
                        f'{value!r}.',
                    )
        else:
            value_cell.value = value
            if label in _TEXT_LABELS:
                value_cell.number_format = '@'
            if label in _WRAP_LABELS:
                value_cell.alignment = LEFT_WRAP_ALIGN
                height = wrapped_row_height(value, 31.0)
                if height is not None:
                    sheet.row_dimensions[row].height = height
            else:
                value_cell.alignment = LEFT_ALIGN

            if label == 'CNPJ da contratada' and value:
                digits = _only_digits(value)
                if len(digits) != 14:
                    flag_pendencia(
                        value_cell,
                        f'CNPJ com {len(digits)} dígito(s), esperado 14.',
                    )

        row += 1

    if (
        inicio_dt is not None
        and termino_dt is not None
        and inicio_dt > termino_dt
    ):
        flag_pendencia(
            cast(
                Cell,
                sheet.cell(row=row_by_label['Término da vigência'], column=4),
            ),
            'Início da vigência posterior ao término — revisar datas.',
        )

    last_identificacao_row = row - 1

    if objetos_path is not None:
        row += 1  # linha em branco entre seções
        _write_objetos_section(sheet, objetos_path, row, warnings)
        last_row = sheet.max_row
    else:
        last_row = last_identificacao_row

    setup_institutional_print(
        sheet,
        contract_number=numero_contrato,
        last_row=last_row,
        last_column=(
            _DADOS_CONTRATUAIS_VALUE_COL
            if dados_contratuais_path is not None
            else 4
        ),
        first_column=2,
    )
    return CapaContext(numero_contrato)


def _write_dados_contratuais_block(
    sheet: Worksheet,
    path: Path,
    warnings: list[str],
) -> None:
    """Bloco complementar "Dados Contratuais" na aba Capa (colunas F/G).
    Lê os pares campo/valor de `dados_contratuais.yaml` e escreve uma linha
    por par, alinhado ao mesmo cabeçalho da seção de identificação (linha
    `_ROW_HEADER`): coluna F = Campo, G = Valor, com zebra alternada, bordas
    finas e quebra de texto para valores longos. Preserva o texto original do
    CSV (nunca interpreta `25%` como número) — a coerção que o Excel faria ao
    colar (ex.: `25%` → 0,25) é evitada de propósito."""
    try:
        fields = read_dados_contratuais_fields(path)
    except FileNotFoundError:
        warnings.append(
            f'sintetico.xlsx: {path} não encontrado — bloco de dados '
            f"contratuais não anexado à aba '{CAPA_SHEET_NAME}'"
        )
        return
    except (OSError, ValueError) as exc:
        warnings.append(
            f'sintetico.xlsx: falha ao ler {path}: {exc} — bloco de dados '
            f"contratuais não anexado à aba '{CAPA_SHEET_NAME}'"
        )
        return

    sheet.column_dimensions[
        get_column_letter(_DADOS_CONTRATUAIS_LABEL_COL)
    ].width = _DADOS_CONTRATUAIS_LABEL_WIDTH
    sheet.column_dimensions[
        get_column_letter(_DADOS_CONTRATUAIS_VALUE_COL)
    ].width = _DADOS_CONTRATUAIS_VALUE_WIDTH

    label_header = sheet.cell(
        row=_ROW_HEADER,
        column=_DADOS_CONTRATUAIS_LABEL_COL,
        value='Campo',
    )
    label_header.font = HEADER_FONT
    label_header.fill = HEADER_FILL
    value_header = sheet.cell(
        row=_ROW_HEADER,
        column=_DADOS_CONTRATUAIS_VALUE_COL,
        value='Valor',
    )
    value_header.font = HEADER_FONT
    value_header.fill = HEADER_FILL

    row = _ROW_BODY_START
    for index, (label, value) in enumerate(fields.items()):
        row_fill = SUBSTITUTO_FILL if index % 2 == 1 else None

        field_cell = cast(
            Cell, sheet.cell(row=row, column=_DADOS_CONTRATUAIS_LABEL_COL)
        )
        field_cell.value = label
        field_cell.font = BODY_FONT
        field_cell.alignment = LEFT_ALIGN
        field_cell.border = THIN_BORDER
        if row_fill is not None:
            field_cell.fill = row_fill

        value_cell = cast(
            Cell, sheet.cell(row=row, column=_DADOS_CONTRATUAIS_VALUE_COL)
        )
        value_cell.value = value
        value_cell.font = BODY_FONT
        value_cell.alignment = LEFT_WRAP_ALIGN
        value_cell.border = THIN_BORDER
        value_cell.number_format = '@'
        if row_fill is not None:
            value_cell.fill = row_fill
        height = wrapped_row_height(value, _DADOS_CONTRATUAIS_VALUE_WIDTH)
        if height is not None:
            sheet.row_dimensions[row].height = height

        row += 1


def _write_objetos_section(
    sheet: Worksheet,
    objetos_path: Path,
    header_row: int,
    warnings: list[str],
) -> None:
    """Seção 3 — Item/Categoria/Valor, lida diretamente de `objetos.csv`
    (mantém o texto da Categoria, que `objetos.read_objetos` descarta)."""
    try:
        with objetos_path.open(encoding=OBJETOS_ENCODING, newline='') as handle:
            rows = list(csv.DictReader(handle, delimiter=OBJETOS_DELIMITER))
    except FileNotFoundError:
        warnings.append(
            f'sintetico.xlsx: {objetos_path} não encontrado — dados de '
            f"objetos não anexados à aba '{CAPA_SHEET_NAME}'"
        )
        return
    except OSError as exc:
        warnings.append(
            f'sintetico.xlsx: falha ao ler {objetos_path}: {exc} — dados de '
            f"objetos não anexados à aba '{CAPA_SHEET_NAME}'"
        )
        return

    # Colunas B/C/D (A é o recuo visual da Seção 2, reaproveitado aqui).
    for column, label in zip(
        (2, 3, 4), ('Item', 'Categoria', 'Valor'), strict=True
    ):
        cell = sheet.cell(row=header_row, column=column, value=label)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = CENTER_ALIGN if label == 'Item' else LEFT_ALIGN

    row = header_row + 1
    for index, entry in enumerate(rows):
        item = (entry.get('Item') or '').strip()
        categoria = (entry.get('Categoria') or '').strip()
        valor_raw = (entry.get('Valor') or '').strip()
        row_fill = SUBSTITUTO_FILL if index % 2 == 1 else None

        item_cell = sheet.cell(row=row, column=2, value=item)
        item_cell.font = BODY_FONT
        item_cell.alignment = CENTER_ALIGN
        item_cell.border = THIN_BORDER
        if row_fill is not None:
            item_cell.fill = row_fill

        categoria_cell = sheet.cell(row=row, column=3, value=categoria)
        categoria_cell.font = BODY_FONT
        categoria_cell.alignment = LEFT_ALIGN
        categoria_cell.border = THIN_BORDER
        if row_fill is not None:
            categoria_cell.fill = row_fill
        if categoria == _CATEGORIA_PENDENCIA:
            flag_pendencia(categoria_cell, _CATEGORIA_PENDENCIA_MSG)
        elif not categoria:
            flag_pendencia(categoria_cell, 'Categoria ausente para este item.')

        valor_cell = cast(Cell, sheet.cell(row=row, column=4))
        valor_cell.font = BODY_FONT
        valor_cell.alignment = LEFT_ALIGN
        valor_cell.border = THIN_BORDER
        if row_fill is not None:
            valor_cell.fill = row_fill
        try:
            valor_cell.value = float(parse_brl_value(valor_raw))
            valor_cell.number_format = '"R$"\\ #,##0.00'
            valor_cell.alignment = Alignment(
                horizontal='right', vertical='center'
            )
        except (TypeError, ValueError):
            valor_cell.value = valor_raw
            if valor_raw:
                flag_pendencia(
                    valor_cell,
                    f'Valor monetário inválido: {valor_raw!r}.',
                )
        row += 1

    total_row = row
    sheet.cell(row=total_row, column=3, value='Total mensal').font = LABEL_FONT
    total_cell = cast(Cell, sheet.cell(row=total_row, column=4))
    if row > header_row + 1:
        total_cell.value = f'=SUM(D{header_row + 1}:D{row - 1})'
    total_cell.number_format = '"R$"\\ #,##0.00'
    total_cell.font = LABEL_FONT
    total_cell.alignment = Alignment(horizontal='right', vertical='center')
