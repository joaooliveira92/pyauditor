"""`perfis_profissionais.csv` — perfis profissionais do contrato, exibidos em
seção própria na aba `Equipe` do `sintetico.xlsx` (colunas ITEM/CATEGORIA/
quantidades/CBO/denominação/presencial-remoto).

O arquivo é uma planilha CSV simples com cabeçalho e uma linha por perfil
(com `,` como delimitador; campos com vírgula vêm entre aspas). Malformado é
falha técnica (`ValueError`); arquivo *ausente* é dado incompleto — decisão do
chamador (warning + seção omitida), mesmo contrato de `objetos.py`/`equipe.py`.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Final

PERFIS_PROFISSIONAIS_FILENAME: Final[str] = 'perfis_profissionais.csv'
PERFIS_DELIMITER: Final[str] = ','
PERFIS_ENCODING: Final[str] = 'utf-8-sig'

N_ITEM_HEADER: Final[str] = 'Nº ITEM'
CATEGORIA_HEADER: Final[str] = 'CATEGORIA'
QUANTIDADE_TOTAL_HEADER: Final[str] = 'QUANTIDADE TOTAL DE PROFISSIONAIS'
CBO_HEADER: Final[str] = 'CBO'
DENOMINACAO_HEADER: Final[str] = 'DENOMINAÇÃO DO PERFIL'
QUANTIDADE_HEADER: Final[str] = 'QUANTIDADE'
PRESENCIAL_HEADER: Final[str] = 'PRESENCIAL/REMOTO'

_PERFIS_HEADERS: Final[frozenset[str]] = frozenset(
    {
        N_ITEM_HEADER,
        CATEGORIA_HEADER,
        QUANTIDADE_TOTAL_HEADER,
        CBO_HEADER,
        DENOMINACAO_HEADER,
        QUANTIDADE_HEADER,
        PRESENCIAL_HEADER,
    }
)


def read_perfis_profissionais(path: Path) -> list[dict[str, str]]:
    """Lê `perfis_profissionais.csv` — uma linha por perfil, na ordem do
    arquivo. Valida o cabeçalho (colunas obrigatórias); valores ausentes
    ficam como '' na linha.

    Raises:
        FileNotFoundError: arquivo ausente — dado incompleto, o chamador
            decide (warning + seção omitida).
        ValueError: malformado — cabeçalho divergente ou CSV vazio.
    """
    with path.open(encoding=PERFIS_ENCODING, newline='') as handle:
        reader = csv.DictReader(handle, delimiter=PERFIS_DELIMITER)
        if reader.fieldnames is None:
            raise ValueError(f'{path}: CSV vazio ou sem cabeçalho')
        fieldnames = [name.strip() for name in reader.fieldnames]
        if not _PERFIS_HEADERS.issubset(set(fieldnames)):
            raise ValueError(
                f'{path}: cabeçalho esperado '
                f"'Nº ITEM,CATEGORIA,QUANTIDADE TOTAL DE PROFISSIONAIS,"
                f"CBO,DENOMINAÇÃO DO PERFIL,QUANTIDADE,PRESENCIAL/REMOTO'"
            )
        rows = list(reader)

    perfis: list[dict[str, str]] = []
    for row in rows:
        if not any((row.get(h) or '').strip() for h in _PERFIS_HEADERS):
            continue  # linha em branco residual — ignora
        perfis.append({h: (row.get(h) or '').strip() for h in _PERFIS_HEADERS})
    return perfis
