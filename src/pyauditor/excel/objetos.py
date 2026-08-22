"""Valores contratuais mensais lidos de ``input/objetos.csv``.

O arquivo é a fonte monetária canônica dos itens contratuais e usa
exatamente o esquema:

    Item,Categoria,Valor

Cada linha representa um item contratual:

- ``Item`` é um inteiro positivo, contíguo e começando em 1;
- ``Categoria`` é um valor descritivo não vazio;
- ``Valor`` é o valor mensal do item.

Valores monetários podem usar notação brasileira, como ``R$ 148.205,54``,
ou notação de máquina, como ``148205.54``. Separadores de milhar
brasileiros são opcionais, mas valores decimais devem ter exatamente duas
casas.

Os valores são representados com :class:`decimal.Decimal` para evitar erros
de ponto flutuante binário nos totais contratuais. O total mensal é a soma
exata de todos os itens; o total anual é o mensal multiplicado por doze.

O arquivo não carrega linha de resumo. Por isso não há total declarado
pelo fiscal para reconciliar contra os totais calculados.

Arquivo ausente não é tratado aqui: ``FileNotFoundError`` propaga para o
chamador decidir se a ausência é entrada incompleta ou condição fatal.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Final

__all__: Final[tuple[str, ...]] = (
    'OBJETOS_DELIMITER',
    'OBJETOS_ENCODING',
    'OBJETOS_FILENAME',
    'Objetos',
    'parse_brl_value',
    'read_objetos',
)

OBJETOS_FILENAME: Final[str] = 'objetos.csv'
OBJETOS_DELIMITER: Final[str] = ','
OBJETOS_ENCODING: Final[str] = 'utf-8-sig'

_ITEM_HEADER: Final[str] = 'Item'
_CATEGORIA_HEADER: Final[str] = 'Categoria'
_VALOR_HEADER: Final[str] = 'Valor'

_EXPECTED_HEADERS: Final[tuple[str, ...]] = (
    _ITEM_HEADER,
    _CATEGORIA_HEADER,
    _VALOR_HEADER,
)

_MONTHS_PER_YEAR: Final[Decimal] = Decimal('12')
_ZERO: Final[Decimal] = Decimal('0.00')

_PT_BR_MONEY_RE: Final[re.Pattern[str]] = re.compile(
    r"""
    ^\s*
    (?:R\$\s*)?
    (?P<integer>
        0
        |
        [1-9]\d*
        |
        [1-9]\d{0,2}(?:\.\d{3})+
    )
    (?P<decimal>,\d{2})?
    \s*$
    """,
    re.VERBOSE,
)

_MACHINE_MONEY_RE: Final[re.Pattern[str]] = re.compile(
    r"""
    ^\s*
    (?P<integer>0|[1-9]\d*)
    (?P<decimal>\.\d{2})?
    \s*$
    """,
    re.VERBOSE,
)


@dataclass(frozen=True, slots=True)
class Objetos:
    """Valores contratuais validados e totais derivados.

    ``itens`` ordena os valores mensais pelo índice contratual de 1..N
    (posição zero corresponde ao item contratual 1). ``total_mensal`` é a
    soma exata dos itens; ``total_anual`` é o mensal multiplicado por doze.
    ``warnings`` reserva diagnósticos não fatais da leitura — o parser
    estrito atual não emite warnings, mas o campo permanece por contrato de
    resultado.
    """

    itens: tuple[Decimal, ...]
    total_mensal: Decimal
    total_anual: Decimal
    warnings: tuple[str, ...]


def parse_brl_value(text: str) -> Decimal:
    """Converte um valor monetário suportado em ``Decimal`` exato.

    Representações brasileiras aceitas: ``R$ 148.205,54``, ``148.205,54``,
    ``148205,54``, ``148205``, ``R$ 0,00``. Representações de máquina
    aceitas: ``148205.54``, ``148205``, ``0.00``.

    Separadores de milhar seguem o agrupamento brasileiro; valores decimais
    devem ter exatamente duas casas. Valores negativos, separadores
    malformados, símbolos de moeda além de ``R$`` e valores não numéricos
    são rejeitados.
    """
    if not isinstance(text, str):
        raise TypeError(
            f'valor monetário deve ser string, recebido {type(text).__name__}.'
        )

    pt_br_match = _PT_BR_MONEY_RE.fullmatch(text)
    if pt_br_match is not None:
        integer_part = pt_br_match.group('integer').replace('.', '')
        decimal_part = pt_br_match.group('decimal') or ',00'
        normalized = f'{integer_part}.{decimal_part[1:]}'
        return _to_decimal(normalized, original=text)

    machine_match = _MACHINE_MONEY_RE.fullmatch(text)
    if machine_match is not None:
        integer_part = machine_match.group('integer')
        decimal_part = machine_match.group('decimal') or '.00'
        normalized = f'{integer_part}{decimal_part}'
        return _to_decimal(normalized, original=text)

    raise ValueError(f'valor monetário inválido: {text!r}.')


def read_objetos(path: Path) -> Objetos:
    """Lê e valida a fonte monetária contratual.

    O cabeçalho deve ser exatamente ``Item,Categoria,Valor``, na ordem e
    grafia informadas. Cada linha de dados deve ter exatamente três campos.

    Os índices de item podem vir em qualquer ordem, mas, após ordenar,
    devem formar a sequência contígua ``1..N``. Índices duplicados,
    ausentes, zero ou negativos são rejeitados.

    Exige pelo menos um item contratual. Categorias não podem ser vazias e
    os valores monetários devem satisfazer :func:`parse_brl_value`.
    """
    indexed_values: list[tuple[int, Decimal]] = []

    with path.open(
        mode='r',
        encoding=OBJETOS_ENCODING,
        newline='',
    ) as handle:
        reader = csv.DictReader(
            handle,
            delimiter=OBJETOS_DELIMITER,
            strict=True,
        )

        if reader.fieldnames is None:
            raise ValueError(f'{path}: CSV vazio ou sem cabeçalho.')

        actual_headers = tuple(reader.fieldnames)
        if actual_headers != _EXPECTED_HEADERS:
            expected = OBJETOS_DELIMITER.join(_EXPECTED_HEADERS)
            actual = OBJETOS_DELIMITER.join(actual_headers)
            raise ValueError(
                f'{path}: cabeçalho inválido: esperado {expected!r}, recebido'
                f'{actual!r}.'
            )

        for row in reader:
            line_number = reader.line_num
            _validate_row_structure(
                path=path,
                line_number=line_number,
                row=row,
            )

            item_raw = _required_field(
                path=path,
                line_number=line_number,
                row=row,
                header=_ITEM_HEADER,
            )
            categoria = _required_field(
                path=path,
                line_number=line_number,
                row=row,
                header=_CATEGORIA_HEADER,
            )
            valor_raw = _required_field(
                path=path,
                line_number=line_number,
                row=row,
                header=_VALOR_HEADER,
            )

            item = _parse_item_index(
                path=path,
                line_number=line_number,
                value=item_raw,
            )

            if not categoria:
                raise ValueError(
                    f'{path}: linha {line_number}: Categoria não pode servazio.'
                )

            try:
                valor = parse_brl_value(valor_raw)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f'{path}: linha {line_number}: Valor inválido para o item'
                    f'{item}: '
                    f'{valor_raw!r}.'
                ) from exc

            indexed_values.append((item, valor))

    if not indexed_values:
        raise ValueError(f'{path}: CSV sem itens contratuais.')

    indexed_values.sort(key=lambda entry: entry[0])
    actual_indexes = tuple(item for item, _ in indexed_values)
    expected_indexes = tuple(range(1, len(indexed_values) + 1))

    if actual_indexes != expected_indexes:
        raise ValueError(
            f'{path}: índices de item devem ser únicos e contíguos a partir de'
            f'1: '
            f'esperado {expected_indexes!r}, recebido {actual_indexes!r}.'
        )

    item_values = tuple(value for _, value in indexed_values)
    total_mensal = sum(item_values, start=_ZERO)
    total_anual = total_mensal * _MONTHS_PER_YEAR

    return Objetos(
        itens=item_values,
        total_mensal=total_mensal,
        total_anual=total_anual,
        warnings=(),
    )


def _to_decimal(normalized: str, *, original: str) -> Decimal:
    """Converte uma string monetária normalizada em ``Decimal``."""
    try:
        value = Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError(f'valor monetário inválido: {original!r}.') from exc

    if not value.is_finite():
        raise ValueError(f'valor monetário deve ser finito: {original!r}.')

    if value < _ZERO:
        raise ValueError(
            f'valor monetário não pode ser negativo: {original!r}.'
        )

    return value


def _validate_row_structure(
    *,
    path: Path,
    line_number: int,
    row: dict[str | None, str | list[str] | None],
) -> None:
    """Valida que a linha do CSV contém exatamente os campos esperados."""
    extra_fields = row.get(None)
    if extra_fields:
        raise ValueError(
            f'{path}: linha {line_number}: campos extras inesperados:'
            f'{extra_fields!r}.'
        )

    missing_headers = tuple(
        header for header in _EXPECTED_HEADERS if row.get(header) is None
    )
    if missing_headers:
        raise ValueError(
            f'{path}: linha {line_number}: campos ausentes para as colunas'
            f'{missing_headers!r}.'
        )


def _required_field(
    *,
    path: Path,
    line_number: int,
    row: dict[str | None, str | list[str] | None],
    header: str,
) -> str:
    """Devolve um campo escalar sem espaços de uma linha CSV estruturalmente
    válida."""
    value = row.get(header)

    if not isinstance(value, str):
        raise ValueError(
            f'{path}: linha {line_number}: campo {header!r} deve ser escalar.'
        )

    stripped = value.strip()
    if not stripped:
        raise ValueError(
            f'{path}: linha {line_number}: campo {header!r} não pode ser vazio.'
        )

    return stripped


def _parse_item_index(
    *,
    path: Path,
    line_number: int,
    value: str,
) -> int:
    """Valida e converte um índice de item contratual positivo."""
    if not value.isascii() or not value.isdecimal():
        raise ValueError(
            f'{path}: linha {line_number}: Item deve ser um inteiro ASCII'
            f'positivo, '
            f'recebido {value!r}.'
        )

    item = int(value)
    if item < 1:
        raise ValueError(
            f'{path}: linha {line_number}: Item deve ser no mínimo 1, recebido'
            f'{item}.'
        )

    return item
