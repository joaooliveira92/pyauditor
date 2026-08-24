"""Estruturação de `categorias.yaml` como dado de formulário para Wayfinder
(ticket 04 do map `config-forms`) — mesmo padrão do `inms.py`: descobre o
arquivo per-órgão, devolve o dict do YAML plano, valida com o modelo
pydantic (`CategoriasFile`) antes de escrever de volta.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from pyauditor.config.categorias import CategoriasFile

try:
    from . import _family_paths as fp
except ImportError:  # python3 server.py — run as a script, not a package
    import _family_paths as fp  # ty: ignore[unresolved-import]

__all__ = (
    'read_categoria',
    'save_categoria',
)

_FILENAME = 'categorias.yaml'


def _resolve_dir(workspace: Path, orgao: str) -> Path:
    for path in fp.resolve_candidates(workspace, _FILENAME):
        if path.parent.name == orgao:
            return path
    raise ValueError(f'{_FILENAME} não encontrado para o órgão {orgao!r}')


def read_categoria(workspace: Path, orgao: str) -> dict[str, Any]:
    """Devolve o `categorias.yaml` de *orgao* como dict de formulário."""
    path = _resolve_dir(workspace, orgao)
    raw = yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(raw, dict):
        raise ValueError(f'{path}: categorias YAML deve ser um dict')
    return {
        'orgao': orgao,
        'path': path.relative_to(workspace).as_posix(),
        'config': raw,
    }


def save_categoria(workspace: Path, payload: dict[str, Any]) -> None:
    """Valida e escreve de volta o `categorias.yaml` de *payload*.

    ``payload`` tem a forma do doc devolvido por `read_categoria`.
    """
    path = fp.resolve_write_path(
        workspace, str(payload.get('path', '')), _FILENAME
    )
    raw = payload.get('config')
    try:
        CategoriasFile.model_validate(raw)
    except ValueError as exc:
        raise ValueError(f'{path}: config inválida — {exc}') from exc
    fp.write_yaml(path, raw)
