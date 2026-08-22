"""Constantes/estilo compartilhados pelos renderers do `sintetico.xlsx` —
extraídas de `excel/sintetico/workbook.py` (ticket 04 SRP).

Colunas típicas + labels + ordem de categorias do INMS 1.14; os renderers
por-shape (`_sheets/*.py`) importam daqui e o dispatcher (`workbook.py`)
fornece os inputs por-INMS.

Os nomes públicos (sem underscore) são a API dos renderers; os aliases `_*`
mantêm a coincidência com os nomes originais do módulo monolítico.
"""

from __future__ import annotations

from typing import Final

from pyauditor.config.niveis import NIVEL_BY_CATEGORIA, NIVEL_ORDER
from pyauditor.engine.strategies import meets_target

__all__: Final[tuple[str, ...]] = (
    'ATIVO_COLUMNS',
    'ATIVO_SUBTOTAL_COLUMNS',
    'CAPA_SHEET_NAME',
    'COLUMNS',
    'EQUIPE_SHEET_NAME',
    'INMS_1_14_CATEGORIA_ORDER',
    'NAO_ATIVADO_TEXT',
    'OUTROS_LABEL',
    'SUBTOTAL_COLUMNS',
    'WHOLE_INDICATOR_LABEL',
    '_ATIVO_COLUMNS',
    '_ATIVO_SUBTOTAL_COLUMNS',
    '_CAPA_SHEET_NAME',
    '_COLUMNS',
    '_EQUIPE_SHEET_NAME',
    '_INMS_1_14_CATEGORIA_ORDER',
    '_NAO_ATIVADO_TEXT',
    '_NIVEL_BY_CATEGORIA',
    '_NIVEL_ORDER',
    '_OUTROS_LABEL',
    '_SUBTOTAL_COLUMNS',
    '_WHOLE_INDICATOR_LABEL',
    'meta_atingida_display',
)

CAPA_SHEET_NAME: Final[str] = 'Capa'
EQUIPE_SHEET_NAME: Final[str] = 'Equipe'

OUTROS_LABEL: Final[str] = 'outros (não contabilizado na meta)'
WHOLE_INDICATOR_LABEL: Final[str] = '(indicador inteiro)'
NAO_ATIVADO_TEXT: Final[str] = (
    'Esse serviço não foi requisitado no período selecionado.'
)

COLUMNS: Final[tuple[str, ...]] = (
    'Categoria',
    'Nível',
    'Grupo executor',
    'Linhas',
    'Dentro do prazo',
    'Fora do prazo',
    '% bruto',
    'Tempo médio criação→resolução',
)
SUBTOTAL_COLUMNS: Final[tuple[str, ...]] = (
    'Nível',
    'Linhas',
    'Dentro do prazo',
    'Fora do prazo',
    '% bruto',
    'Tempo médio criação→resolução',
)

ATIVO_COLUMNS: Final[tuple[str, ...]] = (
    'Categoria',
    'Nível',
    'Ativo',
    'Linhas',
    'Dentro do prazo',
    'Fora do prazo',
    '% bruto',
    'Tempo médio criação→resolução',
)
ATIVO_SUBTOTAL_COLUMNS: Final[tuple[str, ...]] = (
    'Categoria',
    'Linhas',
    'Dentro do prazo',
    'Fora do prazo',
    '% bruto',
    'Tempo médio criação→resolução',
)
# Ordem fixa da spec §14.5: bloco NOC/SOC antes do bloco Operação N3,
# independente da ordem de declaração em categorias.yaml.
INMS_1_14_CATEGORIA_ORDER: Final[tuple[str, ...]] = (
    'MONITORAMENTO_NOC_SOC',
    'OPERACAO_N3',
)


def meta_atingida_display(
    value: float, target_operator: str, target_value: float
) -> str:
    """`"Sim"`/`"Não"` conforme `meets_target` — reusado pelos renderers
    precomputed e ratio/sum ("Meta atingida?" derivada de `target`, não da
    coluna crua do CSV)."""
    return (
        'Sim' if meets_target(value, target_operator, target_value) else 'Não'
    )


# Aliases de compatibilidade com os nomes internos do módulo monolítico.
_COLUMNS = COLUMNS
_SUBTOTAL_COLUMNS = SUBTOTAL_COLUMNS
_ATIVO_COLUMNS = ATIVO_COLUMNS
_ATIVO_SUBTOTAL_COLUMNS = ATIVO_SUBTOTAL_COLUMNS
_INMS_1_14_CATEGORIA_ORDER = INMS_1_14_CATEGORIA_ORDER
_OUTROS_LABEL = OUTROS_LABEL
_WHOLE_INDICATOR_LABEL = WHOLE_INDICATOR_LABEL
_NAO_ATIVADO_TEXT = NAO_ATIVADO_TEXT
_CAPA_SHEET_NAME = CAPA_SHEET_NAME
_EQUIPE_SHEET_NAME = EQUIPE_SHEET_NAME
# Categoria→Nível é dono único em `config/niveis.py` (ticket 11).
_NIVEL_ORDER = NIVEL_ORDER
_NIVEL_BY_CATEGORIA = NIVEL_BY_CATEGORIA
