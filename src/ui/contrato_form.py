"""Estruturação do bundle "Contrato" como dado de formulário para Wayfinder
(ticket 05 do map `config-forms`) — três arquivos globais pequenos, sem
órgão, cada um um dict campo/valor achatado (`dados_contratuais.yaml`,
`ajuste_inms.yaml`, `desconto_regulatório.yaml`). Decisão do charting: uma
tela só que cobre os três, não três formulários separados; nenhum dos três
tem modelo pydantic hoje (`ajuste_inms`/`desconto_regulatório` nem são lidos
pelo pipeline, só documentam a fórmula/descrição usadas no `sintetico.xlsx`)
— a validação aqui é a mesma que `excel/dados_contratuais.py` já assume:
mapeamento raso de string para string.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Final

import yaml

try:
    from . import _family_paths as fp
except ImportError:  # python3 server.py — run as a script, not a package
    import _family_paths as fp  # ty: ignore[unresolved-import]

__all__ = (
    'read_contrato',
    'save_contrato',
)

_FILES: Final[dict[str, str]] = {
    'dados_contratuais': 'dados_contratuais.yaml',
    'ajuste_inms': 'ajuste_inms.yaml',
    'desconto_regulatorio': 'desconto_regulatório.yaml',
}


def _resolve_path(workspace: Path, filename: str) -> Path:
    candidates = fp.resolve_candidates(workspace, filename)
    if not candidates:
        raise ValueError(f'{filename} não encontrado no workspace')
    return candidates[0]


def _load_kv(path: Path) -> dict[str, str]:
    raw = yaml.safe_load(path.read_text(encoding='utf-8'))
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError(f'{path}: esperado um mapeamento campo -> valor')
    return {str(key): str(value) for key, value in raw.items()}


def _validate_kv(config: Any, section: str) -> dict[str, str]:
    if not isinstance(config, dict):
        raise ValueError(f'{section}: esperado um mapeamento campo -> valor')
    result: dict[str, str] = {}
    for key, value in config.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError(f'{section}: chaves e valores devem ser texto')
        result[key] = value
    return result


def read_contrato(workspace: Path) -> dict[str, Any]:
    """Devolve os três arquivos do bundle como um único doc de formulário."""
    result: dict[str, Any] = {}
    for section, filename in _FILES.items():
        path = _resolve_path(workspace, filename)
        result[section] = {
            'path': path.relative_to(workspace).as_posix(),
            'config': _load_kv(path),
        }
    return result


def save_contrato(workspace: Path, payload: dict[str, Any]) -> None:
    """Valida e escreve de volta cada arquivo presente em *payload*.

    ``payload`` tem a forma do doc devolvido por `read_contrato`; seções
    ausentes são ignoradas (nenhuma delas depende das outras).
    """
    writes: list[tuple[Path, dict[str, str]]] = []
    for section, filename in _FILES.items():
        entry = payload.get(section)
        if entry is None:
            continue
        path = fp.resolve_write_path(
            workspace, str(entry.get('path', '')), filename
        )
        writes.append((path, _validate_kv(entry.get('config'), section)))

    for path, config in writes:
        fp.write_yaml(path, config)
