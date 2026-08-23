"""Abas institucionais Capa/Equipe/Prazos de `sintetico.xlsx` — revisão de
layout/tipagem/impressão pedida pelo fiscal técnico (spec de revisão
Capa/Equipe/Prazos). Substitui a reprodução verbatim anterior
(`verbatim_sheets.py`): preserva os valores originais (nunca inventa nem
corrige dado contratual), mas aplica identidade visual institucional,
tipagem correta (datas/moeda reais, identificadores como texto), impressão
configurada e sinalização de pendências (preenchimento amarelo-claro +
comentário), nunca correção automática de conteúdo contratual.
"""

from __future__ import annotations

import csv
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Final, NamedTuple, cast

from openpyxl import Workbook
from openpyxl.cell.cell import Cell
from openpyxl.comments import Comment
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from pyauditor.excel._style import (
    BODY_FONT,
    CENTER_ALIGN,
    CRITICIDADE_FILL_BY_VALUE,
    HEADER_FILL,
    HEADER_FONT,
    LABEL_FONT,
    LEFT_ALIGN,
    LEFT_WRAP_ALIGN,
    PENDING_FILL,
    SECTION_FONT,
    SUBSTITUTO_FILL,
    SUBTITLE_FONT,
    THIN_BORDER,
    TITLE_FONT,
    TOP_WRAP_ALIGN,
    setup_institutional_print,
)
from pyauditor.excel.capa import read_capa_csv_fields
from pyauditor.excel.dados_contratuais import read_dados_contratuais_fields
from pyauditor.excel.equipe import EQUIPE_DELIMITER, EQUIPE_ENCODING
from pyauditor.excel.objetos import (
    OBJETOS_DELIMITER,
    OBJETOS_ENCODING,
    parse_brl_value,
)
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
from pyauditor.excel.prazos import PRAZOS_SHEET_NAME, read_prazos
from pyauditor.excel.sintetico._sheets._shared import (
    CAPA_SHEET_NAME,
    EQUIPE_SHEET_NAME,
)

_AUTHOR: Final[str] = 'pyauditor'

_TITLE: Final[str] = (
    'DEMONSTRATIVO DE EXECUÇÃO DOS SERVIÇOS DE INFRAESTRUTURA DE TI'
)
_SECTION_TITLE: Final[str] = 'INFORMAÇÕES INICIAIS'
_SUBTITLE_REF_FORMULA: Final[str] = '=Capa!B2'

# Esqueleto de linhas compartilhado pelas três abas: título do documento,
# subtítulo (na Capa, uma fórmula dinâmica; nas demais, uma referência a
# `Capa!B2` — nunca uma segunda digitação independente), branco, título da
# seção. Capa/Equipe têm 1 branco entre a seção e o cabeçalho da tabela;
# Prazos tem a nota (2 linhas) no lugar desse branco.
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
# `input/dados_contratuais.csv`): colunas F (Campo) e G (Valor), alinhadas ao
# mesmo cabeçalho do bloco B:D — uma linha por par `label;value` do CSV, na
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


class CapaContext(NamedTuple):
    """Número do contrato, usado só no rodapé de Equipe/Prazos — título e
    subtítulo dessas abas nunca redigitam o dado, referenciam `Capa!B2` (a
    fórmula dinâmica) diretamente na própria planilha."""

    numero_contrato: str | None


_CHARS_PER_WIDTH_UNIT: Final = 1.15


def _wrapped_row_height(
    text: str, total_width_chars: float, *, line_height: float = 14.0
) -> float | None:
    """Altura aproximada de uma linha com `wrap_text` (spec §2.2: "alturas de
    linha ajustadas após a aplicação de quebra de texto") — openpyxl não
    recalcula isso sozinho. `total_width_chars` é a soma das larguras de
    coluna abrangidas pela célula (mescladas ou não). Devolve `None` quando
    o texto cabe em uma linha — nesse caso a altura padrão da planilha já
    serve, não há motivo para fixá-la explicitamente. `_CHARS_PER_WIDTH_UNIT`
    é um fator empírico (caracteres em Arial 10 cabem mais densamente que 1
    por unidade de largura do Excel), calibrado contra os casos reais desta
    aba."""
    if not text or total_width_chars <= 0:
        return None
    lines = math.ceil(len(text) / (total_width_chars * _CHARS_PER_WIDTH_UNIT))
    if lines <= 1:
        return None
    return lines * line_height


def _flag_pendencia(cell: Cell, message: str) -> None:
    cell.fill = PENDING_FILL
    cell.comment = Comment(message, _AUTHOR)


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


def _write_capa_sheet(
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
                    _flag_pendencia(
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
                height = _wrapped_row_height(value, 31.0)
                if height is not None:
                    sheet.row_dimensions[row].height = height
            else:
                value_cell.alignment = LEFT_ALIGN

            if label == 'CNPJ da contratada' and value:
                digits = _only_digits(value)
                if len(digits) != 14:
                    _flag_pendencia(
                        value_cell,
                        f'CNPJ com {len(digits)} dígito(s), esperado 14.',
                    )

        row += 1

    if (
        inicio_dt is not None
        and termino_dt is not None
        and inicio_dt > termino_dt
    ):
        _flag_pendencia(
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
    Lê os pares `label;value` de `dados_contratuais.csv` e escreve uma linha
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

        field_cell = sheet.cell(row=row, column=_DADOS_CONTRATUAIS_LABEL_COL)
        field_cell.value = label
        field_cell.font = BODY_FONT
        field_cell.alignment = LEFT_ALIGN
        field_cell.border = THIN_BORDER
        if row_fill is not None:
            field_cell.fill = row_fill

        value_cell = sheet.cell(row=row, column=_DADOS_CONTRATUAIS_VALUE_COL)
        value_cell.value = value
        value_cell.font = BODY_FONT
        value_cell.alignment = LEFT_WRAP_ALIGN
        value_cell.border = THIN_BORDER
        value_cell.number_format = '@'
        if row_fill is not None:
            value_cell.fill = row_fill
        height = _wrapped_row_height(value, _DADOS_CONTRATUAIS_VALUE_WIDTH)
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
            _flag_pendencia(categoria_cell, _CATEGORIA_PENDENCIA_MSG)
        elif not categoria:
            _flag_pendencia(categoria_cell, 'Categoria ausente para este item.')

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
                _flag_pendencia(
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


_SUBSTITUTO_RE: Final = re.compile(r'\s*-?\s*substituto$', re.IGNORECASE)


def _normalize_funcao_display(funcao: str) -> tuple[str, bool]:
    """Convenção única do hífen (spec §4.4): 'X Substituto'/'X - Substituto'
    ambos viram 'X - Substituto'."""
    match = _SUBSTITUTO_RE.search(funcao)
    if match is None:
        return funcao, False
    base = funcao[: match.start()].rstrip()
    return f'{base} - Substituto', True


def _write_equipe_sheet(
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
        nome_height = _wrapped_row_height(nome, 68.9)
        if nome_height is not None:
            sheet.row_dimensions[row].height = nome_height

        if eh_substituto:
            funcao_cell.fill = SUBSTITUTO_FILL
            nome_cell.fill = SUBSTITUTO_FILL
            siape_cell.fill = SUBSTITUTO_FILL

        if not funcao_raw:
            _flag_pendencia(funcao_cell, 'Função ausente.')
        elif funcao_display in seen_funcoes:
            _flag_pendencia(
                funcao_cell, f'Função duplicada: {funcao_display!r}.'
            )
        else:
            seen_funcoes.add(funcao_display)

        if not nome:
            _flag_pendencia(nome_cell, 'Nome ausente.')

        if not siape:
            _flag_pendencia(siape_cell, 'SIAPE ausente.')
        elif not (siape.isdigit() and len(siape) == 7):
            _flag_pendencia(
                siape_cell, f'SIAPE fora do padrão de 7 dígitos: {siape!r}.'
            )
        elif siape in seen_siapes:
            _flag_pendencia(siape_cell, f'SIAPE duplicado: {siape!r}.')
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


def _write_prazos_sheet(
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
        note_height = _wrapped_row_height(sentence, note_width)
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
            _flag_pendencia(
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
        prazo_height = _wrapped_row_height(prazo, 32.83)
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


def write_institutional_sheets(
    workbook: Workbook,
    *,
    capa_path: Path | None,
    dados_contratuais_path: Path | None = None,
    objetos_path: Path | None,
    equipe_path: Path | None,
    perfis_profissionais_path: Path | None = None,
    prazos_path: Path | None,
    warnings: list[str],
) -> None:
    """Ponto de entrada usado por `sintetico/workbook.py`: gera Capa/Equipe/
    Prazos formatadas, nessa ordem — título e subtítulo de Equipe/Prazos
    referenciam a Capa por fórmula (`=Capa!B2`), nunca por segunda
    digitação independente."""
    contexto = CapaContext(None)
    if capa_path is not None:
        contexto = _write_capa_sheet(
            workbook,
            capa_path,
            dados_contratuais_path,
            objetos_path,
            warnings,
        )
    elif objetos_path is not None:
        warnings.append(
            f'sintetico.xlsx: capa_path não informado — dados de '
            f'{objetos_path} não anexados (dependem da aba '
            f"'{CAPA_SHEET_NAME}')"
        )

    if equipe_path is not None:
        _write_equipe_sheet(
            workbook,
            equipe_path,
            perfis_profissionais_path,
            contexto.numero_contrato,
            warnings,
        )

    if prazos_path is not None:
        _write_prazos_sheet(
            workbook, prazos_path, contexto.numero_contrato, warnings
        )
