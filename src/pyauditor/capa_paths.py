"""Resolução única de capa_path (issue 05).

``_capa_path_for`` existia duplicado com lógica divergente entre
``cli/main.py`` e ``orchestration/run.py``. Este módulo é a única
implementação, usada por ambos os entry points.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

_DEFAULT_CAPA_NAME: Final[str] = 'capa.csv'


def resolve_capa_path(capa_path: Path, orgao: str) -> Path:
    """Per-órgão capa CSV ao lado do ``capa.csv`` comum (ticket 07).

    Um ``capa_path`` customizado (``--capa-path meucapa.csv``) vence as-is
    — não é reescrito para ``capa_<orgao>.csv``. Só o default ``capa.csv``
    gera o per-órgão ``capa_<orgao>.csv``.
    """
    if orgao == 'both':
        return capa_path
    if capa_path.name != _DEFAULT_CAPA_NAME:
        return capa_path
    return capa_path.parent / f'capa_{orgao}.csv'
