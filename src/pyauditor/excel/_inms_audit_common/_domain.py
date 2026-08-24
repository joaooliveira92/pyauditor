"""Resolução de grupos compartilhada entre as abas enriquecidas de INMS —
extraída de `excel/inms_1_1/_domain.py` quando o INMS 1.2 ganhou seu próprio
renderer enriquecido.
"""

from __future__ import annotations

from pyauditor.categoria_filter import (
    GRUPO_EXECUTOR_COLUMN,
    compute_categoria_values,
)
from pyauditor.config.categorias import CategoriasFile, GrupoExecutorMode
from pyauditor.excel._inms_audit_common._layout import (
    AUDIT_REVIEW_LABEL,
    NIVEL_BY_CATEGORIA_,
    NO_PRAZO_COLUMN,
    NUM_SOLICITACAO_COLUMN,
    SEM_NIVEL,
)


def build_grupo_rows(
    categorias_file: CategoriasFile,
    grupo_executor_entries: list[tuple[str, GrupoExecutorMode]],
    real_values: set[str],
) -> list[tuple[str, str, str]]:
    """(grupo, nível, categoria_label) — mesma resolução de
    `compute_categoria_values` usada por `_write_grupo_executor_sheet`, para
    que a aba enriquecida cubra exatamente os mesmos grupos/categorias por
    órgão, sem hardcodar nomes de grupo."""
    per_categoria_values, outros_values = compute_categoria_values(
        grupo_executor_entries, real_values
    )
    result: list[tuple[str, str, str]] = []
    for categoria_key, effective_values in per_categoria_values.items():
        categoria = categorias_file.categorias[categoria_key]
        nivel = NIVEL_BY_CATEGORIA_.get(categoria_key, SEM_NIVEL)
        for grupo in sorted(effective_values):
            result.append((grupo, nivel, categoria.label))
    for grupo in sorted(outros_values):
        result.append((grupo, SEM_NIVEL, AUDIT_REVIEW_LABEL))
    # Nota (ticket 14 / M-05): não há checagem extra de unicidade aqui —
    # `compute_categoria_values`, chamada acima, já valida que nenhum grupo
    # pertence a mais de uma categoria (in_values sobrepostos ou
    # catch_all_contains sobrepondo in_values de outra categoria) e lança
    # `ValueError` antes de `per_categoria_values`/`outros_values` existirem.
    # Duplicar essa validação aqui seria código morto.
    return result


def normalize_no_prazo(row: dict[str, str]) -> str:
    """Normaliza o campo "No prazo" do CSV bruto para exatamente "S" ou "N"
    — sem isso, variações como "s", "Sim", "N/A" ou vazio entram no
    denominador (IAP, via `COUNTA`/`ROWS`) mas não em nenhum dos dois
    `COUNTIF` (dentro/fora do prazo), quebrando silenciosamente a
    identidade IAP = dentro + fora."""
    normalized = row[NO_PRAZO_COLUMN].strip().upper()
    if normalized not in {'S', 'N'}:
        num_solicitacao = row.get(NUM_SOLICITACAO_COLUMN, '?')
        raise ValueError(
            f"Nº Solicitação {num_solicitacao!r}: valor de 'No prazo' inválido "
            f"{row[NO_PRAZO_COLUMN]!r} — esperado apenas 'S' ou 'N'"
        )
    return normalized


_REQUIRED_COLUMNS_BASE: tuple[str, ...] = (
    NUM_SOLICITACAO_COLUMN,
    'Atividades',
    'DataHoraSolicitacao',
    'DataHoraLimite',
    'DataHoraFim',
    NO_PRAZO_COLUMN,
    'TecnicoExecutor',
    GRUPO_EXECUTOR_COLUMN,
)


def has_required_columns(
    fieldnames: list[str], *, extra_columns: tuple[str, ...] = ()
) -> bool:
    return all(
        column in fieldnames
        for column in (*_REQUIRED_COLUMNS_BASE, *extra_columns)
    )
