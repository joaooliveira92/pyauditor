"""Dados contratuais complementares da Capa do `sintetico.xlsx` — parâmetros
contratuais em `input/dados_contratuais.yaml` (Fator-K, valor global,
garantias, limites de supressão/acréscimo, prazos de aviso), exibidos em
bloco próprio (colunas F/G) ao lado dos campos de identificação na aba
`Capa`.

Diferente de `capa.csv` — que `bootstrap` cria em branco e o fiscal técnico
preenche a cada competência —, este arquivo é referência contratual estática:
muda só quando o contrato muda (aditivo), nunca por competência, e não tem
writer no pipeline. Por isso vive em YAML campo -> valor, não CSV.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import yaml

DADOS_CONTRATUAIS_FILENAME: Final[str] = 'dados_contratuais.yaml'


def read_dados_contratuais_fields(path: Path) -> dict[str, str]:
    """Lê os pares campo/valor de `dados_contratuais.yaml`.

    Preserva o texto original (nunca interpreta `25%` ou `2,35` como
    número) — todo valor volta como string, mesmo que o YAML o tenha lido
    como outro tipo.

    Raises:
        FileNotFoundError: se o arquivo não existir.
        ValueError: se o YAML não for um mapeamento campo -> valor.
    """
    with path.open(encoding='utf-8') as handle:
        try:
            raw = yaml.safe_load(handle)
        except yaml.YAMLError as exc:
            raise ValueError(f'{path}: YAML malformado: {exc}') from exc
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError(f'{path}: esperado um mapeamento campo -> valor')
    return {str(key): str(value) for key, value in raw.items()}
