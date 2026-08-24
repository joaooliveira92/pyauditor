"""Path-resolution/write helpers shared by the config-forms family modules
(`categorias_form.py`, `datasets_form.py`, `contrato_form.py`) — same shape
`inms.py` already had before three more families needed it, factored out
once it stopped being a single use case.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import yaml

from pyauditor.atomic_write import atomic_write

__all__ = (
    'IGNORED_DIRS',
    'resolve_candidates',
    'resolve_write_path',
    'write_yaml',
)

IGNORED_DIRS: Final[frozenset[str]] = frozenset(
    {'.git', '.venv', 'node_modules', '__pycache__', '.scratch', '.agents'}
)


def resolve_candidates(workspace: Path, filename: str) -> list[Path]:
    """Todo `filename` do workspace, fora de diretórios ignorados."""
    return [
        path
        for path in workspace.rglob(filename)
        if not any(part in IGNORED_DIRS for part in path.parts)
    ]


def resolve_write_path(workspace: Path, relative: str, filename: str) -> Path:
    """Resolve *relative* para escrita: nome esperado + sem escapar do
    workspace."""
    if not relative or Path(relative).name != filename:
        raise ValueError(f'Só {filename} é editável por este formulário')
    candidate = (workspace / relative).resolve()
    if not candidate.is_relative_to(workspace.resolve()):
        raise ValueError('O caminho escapa do workspace configurado')
    return candidate


def write_yaml(path: Path, data: object) -> None:
    """Serializa *data* como YAML e escreve atomicamente em *path*."""

    def _write(tmp_path: Path) -> None:
        tmp_path.write_text(
            yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
            encoding='utf-8',
        )

    atomic_write(path, _write)
