"""Dados contratuais complementares da Capa do `sintetico.xlsx` — parâmetros
contratuais em `input/dados_contratuais.csv` (Fator-K, valor global, garantias,
limites de supressão/acréscimo, prazos de aviso), exibidos em bloco próprio
(colunas F/G) ao lado dos campos de identificação na aba `Capa`.

O arquivo segue o mesmo formato `Campo;Valor` de `capa.csv`; o leitor aqui é
convenientemente o mesmo `read_capa_csv_fields` — os dois arquivos compartilham
a gramática `label;value`, só muda a semântica do conteúdo.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from pyauditor.excel.capa import read_capa_csv_fields

DADOS_CONTRATUAIS_FILENAME: Final[str] = 'dados_contratuais.csv'


def read_dados_contratuais_fields(path: Path) -> dict[str, str]:
    """Lê os pares `label;value` de `dados_contratuais.csv` — mesma gramática
    de `capa.csv` (repõe `read_capa_csv_fields`). Duplicatas lançam
    `ValueError`, igual ao arquivo da capa."""
    return read_capa_csv_fields(path)
