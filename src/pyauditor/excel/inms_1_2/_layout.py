"""Constantes de leiaute da aba INMS 1.2 — as genéricas (compartilhadas com
INMS 1.1) vivem em `excel/_inms_audit_common/_layout.py`; aqui só o que é
específico do shape `segmented_ratio` (3 categorias por prioridade SLA).
"""

from __future__ import annotations

from typing import Final, NamedTuple

from pyauditor.excel._inms_audit_common._layout import AB as _SLA_RAW_COLUMN

# Coluna de prioridade (texto livre, ex. "(CIT) Requisição - Baixa 16
# horas") — usada só por contains-match (config `denominator_filter`), nunca
# parseada para extrair a quantidade de horas embutida no texto (ver
# `excel/_inms_audit_common/_raw_block.py`).
SLA_COLUMN: Final[str] = 'SLA'

# Reaproveita a coluna AB (livre nesta aba — o INMS 1.1 usa AB/AC/AE/AI só
# para o controle contratual bruto, que não se aplica aqui) para guardar o
# texto bruto da coluna SLA, sem precisar renumerar o restante do bloco de
# apoio compartilhado.
SLA_RAW_COLUMN: Final[int] = _SLA_RAW_COLUMN


class CategoryParams(NamedTuple):
    """Um dos 3 sub-ratios do INMS 1.2 (Alta/Média/Baixa) — espelha
    `SegmentedCategory` de `config/models.py`, mas só com o que o renderer
    precisa (nome de exibição, substring de match contra `SLA` e
    `step_points`); mantém o módulo Excel desacoplado do modelo de config."""

    label: str
    sla_contains: str
    step_points: float
