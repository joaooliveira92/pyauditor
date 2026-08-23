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
import re
from datetime import datetime
from pathlib import Path
from typing import Final, NamedTuple

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment
from openpyxl.worksheet.worksheet import Worksheet

from pyauditor.excel._style import (
    BODY_FONT,
    CENTER_ALIGN,
    CENTER_WRAP_ALIGN,
    CRITICIDADE_FILL_BY_VALUE,
    HEADER_FILL,
    HEADER_FONT,
    LABEL_FONT,
    LEFT_ALIGN,
    LEFT_WRAP_ALIGN,
    PENDING_FILL,
    SUBSTITUTO_FILL,
    SUBTITLE_FONT,
    THIN_BORDER,
    TITLE_FONT,
    setup_institutional_print,
)
from pyauditor.excel.capa import read_capa_csv_fields
from pyauditor.excel.equipe import EQUIPE_DELIMITER, EQUIPE_ENCODING
from pyauditor.excel.objetos import (
    OBJETOS_DELIMITER,
    OBJETOS_ENCODING,
    parse_brl_value,
)
from pyauditor.excel.prazos import PRAZOS_SHEET_NAME, read_prazos
from pyauditor.excel.sintetico._sheets._shared import (
    CAPA_SHEET_NAME,
    EQUIPE_SHEET_NAME,
)
from pyauditor.periodo import PeriodoAfericao, format_period_br

_AUTHOR: Final[str] = 'pyauditor'

_TITLE: Final[str] = (
    'DEMONSTRATIVO DE EXECUÇÃO DOS SERVIÇOS DE INFRAESTRUTURA DE TI'
)

# Ordem de exibição da Seção 2 (identificação contratual) — rótulos exatos
# de `input/capa.csv`; campos ausentes no CSV (capas mais antigas, fixtures
# de teste) simplesmente não aparecem.
_IDENTIFICACAO_LABELS: Final[tuple[str, ...]] = (
    'Número do contrato',
    'Processo SEI',
    'Empresa contratada',
    'CNPJ da contratada',
    'Objeto',
    'Termo Aditivo 1',
    'Termo Aditivo 2',
    'Termo Aditivo 3',
    'Vigência',
    'Portaria Equipe',
    'Início da vigência',
    'Término da vigência',
)
_DATE_LABELS: Final[frozenset[str]] = frozenset(
    {'Início da vigência', 'Término da vigência'}
)
_WRAP_LABELS: Final[frozenset[str]] = frozenset({'Objeto', 'Empresa contratada'})
_TEXT_LABELS: Final[frozenset[str]] = frozenset(
    {
        'Número do contrato',
        'Processo SEI',
        'CNPJ da contratada',
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
    """Dados da Capa que a Equipe/Prazos reaproveitam por referência, nunca
    por segunda digitação independente (spec §4.2/§6)."""

    numero_contrato: str | None
    portaria: str | None


def _flag_pendencia(cell: object, message: str) -> None:
    cell.fill = PENDING_FILL  # type: ignore[attr-defined]
    cell.comment = Comment(message, _AUTHOR)  # type: ignore[attr-defined]


def _strip_fields(raw: dict[str, str]) -> dict[str, str]:
    return {label: value.strip() for label, value in raw.items()}


def _parse_data_br(value: str) -> datetime | None:
    try:
        return datetime.strptime(value, '%d/%m/%Y')
    except ValueError:
        return None


def _only_digits(value: str) -> str:
    return re.sub(r'\D', '', value)


def _write_capa_sheet(
    workbook: Workbook,
    capa_path: Path,
    objetos_path: Path | None,
    periodo: PeriodoAfericao | None,
    warnings: list[str],
) -> CapaContext:
    """Aba "Capa": identificação contratual (Seção 2) + itens/valores
    (Seção 3), formatadas conforme a spec de revisão. Devolve o contexto
    que a Equipe usa para exibir/conferir a Portaria sem redigitá-la."""
    try:
        raw_fields = _strip_fields(read_capa_csv_fields(capa_path))
    except FileNotFoundError:
        warnings.append(
            f"sintetico.xlsx: {capa_path} não encontrado — aba "
            f"'{CAPA_SHEET_NAME}' não gerada"
        )
        return CapaContext(None, None)
    except (OSError, ValueError) as exc:
        warnings.append(
            f'sintetico.xlsx: falha ao ler {capa_path}: {exc} — aba '
            f"'{CAPA_SHEET_NAME}' não gerada"
        )
        return CapaContext(None, None)

    numero_contrato = raw_fields.get('Número do contrato') or None
    portaria = raw_fields.get('Portaria Equipe') or None

    sheet = workbook.create_sheet(title=CAPA_SHEET_NAME)
    sheet.sheet_view.showGridLines = False
    sheet.column_dimensions['A'].width = 30
    sheet.column_dimensions['B'].width = 46
    sheet.column_dimensions['C'].width = 20

    row = 1
    sheet.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
    sheet.cell(row=row, column=1, value=_TITLE).font = TITLE_FONT
    row += 1

    subtitulo = f'Contrato nº {numero_contrato}' if numero_contrato else ''
    sheet.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
    sheet.cell(row=row, column=1, value=subtitulo).font = SUBTITLE_FONT
    row += 1

    if periodo is not None:
        sheet.merge_cells(
            start_row=row, start_column=1, end_row=row, end_column=3
        )
        sheet.cell(
            row=row, column=1, value=format_period_br(periodo)
        ).font = BODY_FONT
        row += 1

    row += 1  # linha em branco

    inicio_dt: datetime | None = None
    termino_dt: datetime | None = None

    sheet.cell(row=row, column=1, value='Campo').font = HEADER_FONT
    sheet.cell(row=row, column=1).fill = HEADER_FILL
    sheet.cell(row=row, column=2, value='Valor').font = HEADER_FONT
    sheet.cell(row=row, column=2).fill = HEADER_FILL
    row += 1

    for label in _IDENTIFICACAO_LABELS:
        if label not in raw_fields:
            continue
        value = raw_fields[label]

        label_cell = sheet.cell(row=row, column=1, value=label)
        label_cell.font = LABEL_FONT
        label_cell.alignment = LEFT_ALIGN
        label_cell.border = THIN_BORDER

        value_cell = sheet.cell(row=row, column=2)
        value_cell.font = BODY_FONT
        value_cell.border = THIN_BORDER

        if label in _DATE_LABELS:
            parsed = _parse_data_br(value)
            if parsed is not None:
                value_cell.value = parsed
                value_cell.number_format = 'DD/MM/YYYY'
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
            sheet.cell(row=row - 1, column=2),
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
        last_column=3,
    )
    return CapaContext(numero_contrato, portaria)


def _write_objetos_section(
    sheet: Worksheet,
    objetos_path: Path,
    header_row: int,
    warnings: list[str],
) -> None:
    """Seção 3 — Item/Categoria/Valor, lida diretamente de `objetos.csv`
    (mantém o texto da Categoria, que `objetos.read_objetos` descarta)."""
    try:
        with objetos_path.open(
            encoding=OBJETOS_ENCODING, newline=''
        ) as handle:
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

    for column, label in enumerate(('Item', 'Categoria', 'Valor'), start=1):
        cell = sheet.cell(row=header_row, column=column, value=label)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = CENTER_ALIGN if label == 'Item' else LEFT_ALIGN

    row = header_row + 1
    for entry in rows:
        item = (entry.get('Item') or '').strip()
        categoria = (entry.get('Categoria') or '').strip()
        valor_raw = (entry.get('Valor') or '').strip()

        item_cell = sheet.cell(row=row, column=1, value=item)
        item_cell.font = BODY_FONT
        item_cell.alignment = CENTER_ALIGN
        item_cell.border = THIN_BORDER

        categoria_cell = sheet.cell(row=row, column=2, value=categoria)
        categoria_cell.font = BODY_FONT
        categoria_cell.alignment = LEFT_ALIGN
        categoria_cell.border = THIN_BORDER
        if categoria == _CATEGORIA_PENDENCIA:
            _flag_pendencia(categoria_cell, _CATEGORIA_PENDENCIA_MSG)
        elif not categoria:
            _flag_pendencia(categoria_cell, 'Categoria ausente para este item.')

        valor_cell = sheet.cell(row=row, column=3)
        valor_cell.font = BODY_FONT
        valor_cell.alignment = LEFT_ALIGN
        valor_cell.border = THIN_BORDER
        try:
            valor_cell.value = float(parse_brl_value(valor_raw))
            valor_cell.number_format = '"R$" #,##0.00'
            valor_cell.alignment = Alignment(horizontal='right', vertical='center')
        except (TypeError, ValueError):
            valor_cell.value = valor_raw
            if valor_raw:
                _flag_pendencia(valor_cell, f'Valor monetário inválido: {valor_raw!r}.')
        row += 1

    total_row = row
    sheet.cell(row=total_row, column=2, value='Total mensal').font = LABEL_FONT
    total_cell = sheet.cell(row=total_row, column=3)
    if row > header_row + 1:
        total_cell.value = f'=SUM(C{header_row + 1}:C{row - 1})'
    total_cell.number_format = '"R$" #,##0.00'
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
    capa_portaria: str | None,
    warnings: list[str],
) -> None:
    """Aba "Equipe": FUNÇÃO/NOME/SIAPE formatados, com a Portaria referenciada
    da Capa (nunca redigitada) e pendências sinalizadas por célula, nunca
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
    sheet.column_dimensions['A'].width = 32
    sheet.column_dimensions['B'].width = 42
    sheet.column_dimensions['C'].width = 14

    row = 1
    sheet.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
    sheet.cell(
        row=row, column=1, value='EQUIPE DE GESTÃO E FISCALIZAÇÃO DO CONTRATO'
    ).font = TITLE_FONT
    row += 1

    if capa_portaria:
        sheet.merge_cells(
            start_row=row, start_column=1, end_row=row, end_column=3
        )
        sheet.cell(
            row=row, column=1, value=f'Portaria: {capa_portaria}'
        ).font = SUBTITLE_FONT
        row += 1

    row += 1

    header_row = row
    for column, label in enumerate(('FUNÇÃO', 'NOME', 'SIAPE'), start=1):
        cell = sheet.cell(row=header_row, column=column, value=label)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = CENTER_ALIGN if label == 'SIAPE' else LEFT_ALIGN
    row += 1

    seen_funcoes: set[str] = set()
    seen_siapes: set[str] = set()
    for entry in rows:
        funcao_raw = (entry.get('FUNÇÃO') or '').strip()
        nome = (entry.get('NOME') or '').strip()
        siape = (entry.get('SIAPE') or '').strip()
        if not funcao_raw and not nome and not siape:
            continue

        funcao_display, eh_substituto = _normalize_funcao_display(funcao_raw)

        funcao_cell = sheet.cell(row=row, column=1, value=funcao_display)
        nome_cell = sheet.cell(row=row, column=2, value=nome)
        siape_cell = sheet.cell(row=row, column=3, value=siape)

        funcao_cell.font = BODY_FONT
        funcao_cell.alignment = LEFT_ALIGN
        funcao_cell.border = THIN_BORDER
        nome_cell.font = BODY_FONT
        nome_cell.alignment = LEFT_WRAP_ALIGN
        nome_cell.border = THIN_BORDER
        siape_cell.font = BODY_FONT
        siape_cell.alignment = CENTER_ALIGN
        siape_cell.border = THIN_BORDER
        siape_cell.number_format = '@'

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

    last_row = row - 1
    setup_institutional_print(
        sheet,
        contract_number=None,
        last_row=last_row,
        last_column=3,
        header_row=header_row,
    )


_PRAZO_HORAS_RE: Final = re.compile(
    r'^\s*(\d+)\s*h\s*\(horas corridas\)\s*$', re.IGNORECASE
)
_PRAZOS_NOTE: Final = (
    'Os prazos abaixo constituem parâmetros contratuais de referência. '
    'Eventuais pausas, suspensões ou regras especiais de contagem devem '
    'estar amparadas pelo instrumento contratual ou por evidência formal.'
)


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
    sheet.column_dimensions['A'].width = 22
    sheet.column_dimensions['B'].width = 16
    sheet.column_dimensions['C'].width = 44

    row = 1
    sheet.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
    sheet.cell(
        row=row, column=1, value='PRAZOS MÁXIMOS PARA ATENDIMENTO'
    ).font = TITLE_FONT
    row += 1

    sheet.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
    note_cell = sheet.cell(row=row, column=1, value=_PRAZOS_NOTE)
    note_cell.font = BODY_FONT
    note_cell.alignment = LEFT_WRAP_ALIGN
    sheet.row_dimensions[row].height = 30
    row += 1

    row += 1

    header_labels = tuple(header[:3]) if len(header) >= 3 else (
        'Demanda',
        'Criticidade',
        'Prazo máximo para atendimento',
    )
    header_row = row
    for column, label in enumerate(header_labels, start=1):
        cell = sheet.cell(row=header_row, column=column, value=label)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = CENTER_ALIGN if column == 2 else LEFT_ALIGN
    row += 1

    seen_combos: set[tuple[str, str]] = set()
    for data_row in rows:
        padded = list(data_row) + [''] * (3 - len(data_row))
        demanda = padded[0].strip()
        criticidade = _reformat_criticidade(padded[1])
        prazo = _reformat_prazo_text(padded[2].strip())

        demanda_cell = sheet.cell(row=row, column=1, value=demanda)
        demanda_cell.font = BODY_FONT
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

        criticidade_cell = sheet.cell(row=row, column=2, value=criticidade)
        criticidade_cell.font = BODY_FONT
        criticidade_cell.alignment = CENTER_ALIGN
        criticidade_cell.border = THIN_BORDER
        fill = CRITICIDADE_FILL_BY_VALUE.get(criticidade)
        if fill is not None:
            criticidade_cell.fill = fill

        prazo_cell = sheet.cell(row=row, column=3, value=prazo)
        prazo_cell.font = BODY_FONT
        prazo_cell.alignment = CENTER_WRAP_ALIGN
        prazo_cell.border = THIN_BORDER
        row += 1

    last_row = row - 1
    setup_institutional_print(
        sheet,
        contract_number=contract_number,
        last_row=last_row,
        last_column=3,
        header_row=header_row,
    )


def write_institutional_sheets(
    workbook: Workbook,
    *,
    capa_path: Path | None,
    objetos_path: Path | None,
    equipe_path: Path | None,
    prazos_path: Path | None,
    periodo: PeriodoAfericao | None,
    warnings: list[str],
) -> None:
    """Ponto de entrada usado por `sintetico/workbook.py`: gera Capa/Equipe/
    Prazos formatadas, nessa ordem — Equipe/Prazos reaproveitam contrato/
    portaria lidos da Capa em vez de uma segunda fonte independente."""
    contexto = CapaContext(None, None)
    if capa_path is not None:
        contexto = _write_capa_sheet(
            workbook, capa_path, objetos_path, periodo, warnings
        )
    elif objetos_path is not None:
        warnings.append(
            f'sintetico.xlsx: capa_path não informado — dados de '
            f'{objetos_path} não anexados (dependem da aba '
            f"'{CAPA_SHEET_NAME}')"
        )

    if equipe_path is not None:
        _write_equipe_sheet(workbook, equipe_path, contexto.portaria, warnings)

    if prazos_path is not None:
        _write_prazos_sheet(
            workbook, prazos_path, contexto.numero_contrato, warnings
        )
