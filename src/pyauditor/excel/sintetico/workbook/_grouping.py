from __future__ import annotations

from pyauditor.config.categorias import CategoriasFile

from ._types import InmsEntries


def group_entries_by_inms(
    categorias_file: CategoriasFile,
) -> dict[str, InmsEntries]:
    """Inverte `categorias_file` (indexado por categoria) para indexado por
    `inms_key` — cada INMS pode aparecer em mais de uma categoria (ex.
    Grupo_executor divididos entre categorias distintas)."""
    per_inms: dict[str, InmsEntries] = {}
    for categoria_key, categoria in categorias_file.categorias.items():
        for inms_key, entry in categoria.inms.items():
            per_inms.setdefault(inms_key, []).append((categoria_key, entry))
    return per_inms
