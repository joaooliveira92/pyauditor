"""Constantes e tipos compartilhados pelos demais módulos de `inms_grouped`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from openpyxl.styles import Border, Side

_INMS_BASE_SHEET: Final[str] = 'INMS_BASE'
_INMS_BASE_AGRUPADO_SHEET: Final[str] = 'INMS_BASE_AGRUPADO'
_ORGAOS: Final[tuple[str, ...]] = ('MinC', 'MTur')
_SEM_NIVEL: Final[str] = '—'
_AUDIT_REVIEW_LABEL: Final[str] = 'Grupo sob análise de responsabilidade'
_PERCENT_FMT: Final[str] = '0.00"%";(0.00"%");-'
# Mesma regra de `excel/orgao_consolidation.py` (constantes lá são privadas,
# não importáveis) — só grava "Consolidado" para shapes cujo pooling entre
# órgãos já é validado em outro lugar do pipeline.
_CONSOLIDATABLE_SHAPES: Final[frozenset[str]] = frozenset(
    {'ratio', 'segmented_ratio', 'count_difference'}
)
# INMS "por ativo" (`precomputed_table` com `numerator_column`/
# `denominator_column`/`name_column`) com detalhamento por ativo: 1.4/1.5/
# 1.14 (`PER_ASSET_CONTRACTUAL_IDS` em `excel/orgao_consolidation.py`) e
# 1.9/1.10/1.13, que têm exatamente a mesma forma de config (mesmas 3
# colunas), só não eram indicadores "por ativo" na origem — a mecânica de
# `_ativo_detail_by_inms` não distingue os dois casos.
_PRECOMPUTED_BREAKDOWN_CODES: Final[frozenset[str]] = frozenset(
    {'1.4', '1.5', '1.9', '1.10', '1.13', '1.14'}
)

_COLUMNS: Final[tuple[str, ...]] = (
    'Competência',
    'Item contratual',
    'Serviço',
    'Grupo operacional',
    'Código INMS',
    'Descrição',
    'Órgão',
    'Meta mínima ou máxima',
    'Sentido da meta',
    'Numerador',
    'Denominador',
    'Resultado calculado',
    'Unidade',
    'Conformidade',
    'Diferença para a meta',
)
_COLUMN_WIDTHS: Final[dict[int, int]] = {
    1: 12,
    2: 34,
    3: 34,
    4: 12,
    5: 12,
    6: 42,
    7: 14,
    8: 16,
    9: 12,
    10: 12,
    11: 12,
    12: 16,
    13: 10,
    14: 14,
    15: 16,
}
_TOP_BORDER: Final = Border(top=Side(style='thin', color='1F2937'))

# (categoria, nível, grupo executor, numerador, denominador)
type GrupoRow = tuple[str, str, str, float, float]


@dataclass(frozen=True, slots=True)
class _CodeInfo:
    target_value: float
    target_operator: str
    consolidatable: bool


@dataclass(frozen=True, slots=True)
class GroupedSheetResult:
    """Saída de `add_inms_agrupado_sheet` — as contagens que `consolidate`
    reporta ao usuário (a aba já foi escrita direto no workbook recebido)."""

    code_groups: int
    org_subgroups: int
    total_rows: int
    breakdown_codes: tuple[str, ...]
