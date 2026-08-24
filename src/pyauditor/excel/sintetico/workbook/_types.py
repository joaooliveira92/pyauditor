from __future__ import annotations

from typing import Final

from pyauditor.config.categorias import GrupoExecutorMode, WholeIndicatorMode

InmsEntries = list[tuple[str, GrupoExecutorMode | WholeIndicatorMode]]
"""Uma lista de `(categoria_key, entry)` para um mesmo `inms_key` — a forma
que `categorias_file.categorias[*].inms[inms_key]` assume depois de invertida
por `_grouping.group_entries_by_inms`."""

_INMS_1_1: Final[str] = '1.1'
_INMS_1_2: Final[str] = '1.2'
_INMS_1_14: Final[str] = '1.14'
