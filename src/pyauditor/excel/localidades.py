"""`localidades.csv` — localidades atendidas pelo contrato, exibidas na aba
`Localidades` do `sintetico.xlsx` (endereço, categorias de serviço por
modalidade de execução e quantidade de usuários por local).

Mesmo contrato de `perfis_profissionais.py`: CSV simples com cabeçalho fixo
e uma linha por localidade; malformado é falha técnica (`ValueError`),
arquivo *ausente* é dado incompleto — decisão do chamador (warning + aba
omitida).
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Final

LOCALIDADES_FILENAME: Final[str] = 'localidades.csv'
LOCALIDADES_DELIMITER: Final[str] = ','
LOCALIDADES_ENCODING: Final[str] = 'utf-8-sig'

LOCALIDADE_HEADER: Final[str] = 'LOCALIDADE'
ENDERECO_HEADER: Final[str] = 'ENDEREÇO'
CATEGORIAS_PRESENCIAL_HEADER: Final[str] = (
    'CATEGORIAS DE SERVIÇO (EXECUÇÃO PRESENCIAL)'
)
CATEGORIAS_REMOTA_HEADER: Final[str] = 'CATEGORIAS DE SERVIÇO (EXECUÇÃO REMOTA)'
QUANTIDADE_USUARIOS_HEADER: Final[str] = 'QUANTIDADE DE USUÁRIOS'

_LOCALIDADES_HEADERS: Final[frozenset[str]] = frozenset(
    {
        LOCALIDADE_HEADER,
        ENDERECO_HEADER,
        CATEGORIAS_PRESENCIAL_HEADER,
        CATEGORIAS_REMOTA_HEADER,
        QUANTIDADE_USUARIOS_HEADER,
    }
)


def read_localidades(path: Path) -> list[dict[str, str]]:
    """Lê `localidades.csv` — uma linha por localidade, na ordem do
    arquivo. Valores ausentes ficam como '' na linha.

    Raises:
        FileNotFoundError: arquivo ausente — dado incompleto, o chamador
            decide (warning + aba omitida).
        ValueError: malformado — cabeçalho divergente ou CSV vazio.
    """
    with path.open(encoding=LOCALIDADES_ENCODING, newline='') as handle:
        reader = csv.DictReader(handle, delimiter=LOCALIDADES_DELIMITER)
        if reader.fieldnames is None:
            raise ValueError(f'{path}: CSV vazio ou sem cabeçalho')
        fieldnames = {name.strip() for name in reader.fieldnames}
        if not _LOCALIDADES_HEADERS.issubset(fieldnames):
            raise ValueError(
                f'{path}: cabeçalho esperado '
                f"'{LOCALIDADE_HEADER},{ENDERECO_HEADER},"
                f'{CATEGORIAS_PRESENCIAL_HEADER},'
                f"{CATEGORIAS_REMOTA_HEADER},{QUANTIDADE_USUARIOS_HEADER}'"
            )
        rows = list(reader)

    localidades: list[dict[str, str]] = []
    for row in rows:
        if not any((row.get(h) or '').strip() for h in _LOCALIDADES_HEADERS):
            continue  # linha em branco residual — ignora
        localidades.append(
            {h: (row.get(h) or '').strip() for h in _LOCALIDADES_HEADERS}
        )
    return localidades
