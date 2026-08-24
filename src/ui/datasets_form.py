"""Estruturação de `datasets.yaml` como dado de formulário para Wayfinder
(ticket 03 do map `config-forms`). Só `_shared/datasets.yaml` é lido de fato
pelo pipeline (`config/resolution.py::resolve_config_dir` dá precedência a
`_shared`; ver ticket 02) — este módulo prefere um `datasets.yaml` sob
`_shared/` quando há mais de um candidato no workspace.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from pyauditor.config.manifest import DatasetEntry

try:
    from . import _family_paths as fp
except ImportError:  # python3 server.py — run as a script, not a package
    import _family_paths as fp  # ty: ignore[unresolved-import]

__all__ = (
    'read_datasets',
    'save_datasets',
)

_FILENAME = 'datasets.yaml'


def _resolve_path(workspace: Path) -> Path:
    candidates = fp.resolve_candidates(workspace, _FILENAME)
    if not candidates:
        raise ValueError(f'{_FILENAME} não encontrado no workspace')
    shared = [p for p in candidates if p.parent.name == '_shared']
    return sorted(shared or candidates)[0]


def read_datasets(workspace: Path) -> dict[str, Any]:
    """Devolve o manifest de datasets como dict de formulário."""
    path = _resolve_path(workspace)
    raw = yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(raw, dict) or 'datasets' not in raw:
        raise ValueError(f"{path}: esperado mapeamento com chave 'datasets'")
    entries = raw['datasets']
    if not isinstance(entries, dict):
        raise ValueError(f"{path}: 'datasets' deve ser um mapeamento")
    return {
        'path': path.relative_to(workspace).as_posix(),
        'datasets': entries,
    }


def save_datasets(workspace: Path, payload: dict[str, Any]) -> None:
    """Valida cada entrada (via `DatasetEntry`) e escreve o manifest de volta.

    ``payload`` tem a forma do doc devolvido por `read_datasets`.
    """
    path = fp.resolve_write_path(
        workspace, str(payload.get('path', '')), _FILENAME
    )
    entries = payload.get('datasets')
    if not isinstance(entries, dict):
        raise ValueError("'datasets' deve ser um mapeamento")
    for alias, value in entries.items():
        try:
            DatasetEntry.model_validate(value)
        except ValidationError as exc:
            raise ValueError(f'dataset {alias!r} inválido: {exc}') from exc
    fp.write_yaml(path, {'datasets': entries})
