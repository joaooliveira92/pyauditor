"""Validação de fronteira e resolução de grupos da aba INMS 1.1 — movidas
para `excel/_inms_audit_common/_domain.py` (compartilhadas com outras abas
enriquecidas, ex. INMS 1.2) e reexportadas aqui com os nomes que o resto do
pacote/os testes já usam.
"""

from __future__ import annotations

from pyauditor.config.categorias import CategoriasFile, GrupoExecutorMode
from pyauditor.excel._inms_audit_common._domain import (
    build_grupo_rows,
    normalize_no_prazo,
)
from pyauditor.excel._inms_audit_common._domain import (
    has_required_columns as _has_required_columns,
)

__all__ = ('_build_grupo_rows', '_normalize_no_prazo', 'has_required_columns')


def has_required_columns(fieldnames: list[str]) -> bool:
    return _has_required_columns(fieldnames)


def _build_grupo_rows(
    categorias_file: CategoriasFile,
    grupo_executor_entries: list[tuple[str, GrupoExecutorMode]],
    real_values: set[str],
) -> list[tuple[str, str, str]]:
    return build_grupo_rows(
        categorias_file, grupo_executor_entries, real_values
    )


def _normalize_no_prazo(row: dict[str, str]) -> str:
    return normalize_no_prazo(row)
