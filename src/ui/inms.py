"""Estruturação da config do indicador INMS (YAML) como dado de formulário
para Wayfinder — substitui a edição de YAML cru por um formulário (ticket 01
do wayfinder-ui).

A config de um indicador segmentado vive em dois arquivos:
`_shared/inms-NN.yaml` (contrato, sem `scope`) +
`{orgao}/inms-NN.CATEGORIA.yaml` (parametrização por órgão/categoria). Este
módulo descobre os dois, devolve-os como dicts do YAML plano e os registra
de volta validando com o modelo
pydantic (`IndicatorConfig`). Escrevemos o dict tal como veio (nunca
`model_dump`) para não injetar `scope` nem adicionar campos que o arquivo
não tinha — a serialização é `yaml.safe_dump`, como já faz `split_derive`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

import yaml

from pyauditor.atomic_write import atomic_write
from pyauditor.config.models import IndicatorConfig

__all__ = (
    'IndicatorDoc',
    'SegmentDoc',
    'discover',
    'read_indicator',
    'save_indicator',
)

# Só a convenção de produção: `inms-NN.yaml` (contrato, num de 2 dígitos)
# e `inms-NN.CATEGORIA.yaml` (segmento, categoria em maiúsculas). Os fixtures
# de testes usam o id contratual (`inms-1.1.yaml`) e não devem entrar.
_FILE_RE: Final = re.compile(
    r'^inms-(?P<num>\d{2})(\.(?P<cat>[A-Z0-9_]+))?\.yaml$'
)
_IGNORED_DIRS: Final[frozenset[str]] = frozenset(
    {'.git', '.venv', 'node_modules', '__pycache__'}
)


@dataclass(frozen=True, slots=True)
class SegmentDoc:
    orgao: str
    category: str
    rel_path: str


@dataclass(frozen=True, slots=True)
class IndicatorDoc:
    key: str
    name: str
    shared_rel: str | None
    orgaos: tuple[str, ...]
    segments: tuple[SegmentDoc, ...]


def _key_from_num(num: str) -> str:
    return f'INMS-{num}'


def _num_from_key(key: str) -> str:
    return key.removeprefix('INMS-')


def _indicator_name(raw: dict[str, Any]) -> str:
    indicator = raw.get('indicator')
    if isinstance(indicator, dict):
        name = indicator.get('name')
        if isinstance(name, str):
            return name
    return ''


def _load_raw(path: Path) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(raw, dict):
        raise ValueError(f'{path}: config YAML deve ser um dict')
    return raw


def _resolve(workspace: Path, relative: str) -> Path:
    if not relative or Path(relative).suffix.lower() != '.yaml':
        raise ValueError('Só arquivos .yaml são editáveis como indicador')
    candidate = (workspace / relative).resolve()
    if not candidate.is_relative_to(workspace.resolve()):
        raise ValueError('O caminho escapa do workspace configurado')
    return candidate


def discover(workspace: Path) -> list[IndicatorDoc]:
    """Agrupa os indicadores INMS do workspace por key.

    Um arquivo `inms-NN.yaml` é o contrato compartilhado; um
    `inms-NN.CATEGORIA.yaml` é um segmento parametrizado por órgão (o nome
    do diretório pai é o órgão).
    """
    groups: dict[str, dict[str, Any]] = {}
    for path in workspace.rglob('*.yaml'):
        if any(part in _IGNORED_DIRS for part in path.parts):
            continue
        match = _FILE_RE.match(path.name)
        if match is None:
            continue
        rel = path.relative_to(workspace).as_posix()
        key = _key_from_num(match.group('num'))
        group = groups.setdefault(
            key, {'name': '', 'shared_rel': None, 'segments': []}
        )
        if match.group('cat') is None:
            group['shared_rel'] = rel
            raw = _load_raw(path)
            if 'indicator' in raw:
                group['name'] = _indicator_name(raw)
        else:
            group['segments'].append(
                {
                    'orgao': path.parent.name,
                    'category': match.group('cat'),
                    'rel_path': rel,
                }
            )
    docs: list[IndicatorDoc] = []
    for key, group in groups.items():
        segments = sorted(
            group['segments'],
            key=lambda s: (s['orgao'].casefold(), s['category']),
        )
        docs.append(
            IndicatorDoc(
                key=key,
                name=group['name'],
                shared_rel=group['shared_rel'],
                orgaos=tuple(
                    sorted({s['orgao'] for s in segments}, key=str.casefold)
                ),
                segments=tuple(
                    SegmentDoc(s['orgao'], s['category'], s['rel_path'])
                    for s in segments
                ),
            )
        )
    return docs


def _shared_path(workspace: Path, num: str) -> Path | None:
    for path in workspace.rglob(f'inms-{num}.yaml'):
        if any(part in _IGNORED_DIRS for part in path.parts):
            continue
        return path
    return None


def _segment_paths(workspace: Path, num: str, orgao: str) -> list[Path]:
    result: list[Path] = []
    for path in workspace.rglob(f'inms-{num}.*.yaml'):
        if any(part in _IGNORED_DIRS for part in path.parts):
            continue
        if path.parent.name == orgao:
            result.append(path)
    return sorted(result)


def read_indicator(workspace: Path, key: str, orgao: str) -> dict[str, Any]:
    """Devolve o doc de formulário de um indicador: contrato + segmentos.

    ``shared`` é o dict do arquivo compartilhado (sem `scope`); ``segments``
    são os dicts das configs por categoria do órgão pedido.
    """
    num = _num_from_key(key)
    shared_path = _shared_path(workspace, num)
    segments: list[dict[str, Any]] = []
    for path in _segment_paths(workspace, num, orgao):
        match = _FILE_RE.match(path.name)
        if match is None or match.group('cat') is None:
            continue
        segments.append(
            {
                'category': match.group('cat'),
                'path': path.relative_to(workspace).as_posix(),
                'config': _load_raw(path),
            }
        )
    return {
        'key': key,
        'orgao': orgao,
        'shared': (
            {
                'path': shared_path.relative_to(workspace).as_posix(),
                'config': _load_raw(shared_path),
            }
            if shared_path is not None
            else None
        ),
        'segments': segments,
    }


def _validate_and_write(
    workspace: Path, relative: str, raw: dict[str, Any]
) -> None:
    path = _resolve(workspace, relative)
    try:
        IndicatorConfig.model_validate(raw)
    except ValueError as exc:
        raise ValueError(f'{relative}: config inválida — {exc}') from exc

    def _write(tmp_path: Path) -> None:
        tmp_path.write_text(
            yaml.safe_dump(raw, allow_unicode=True, sort_keys=False),
            encoding='utf-8',
        )

    atomic_write(path, _write)


def save_indicator(workspace: Path, payload: dict[str, Any]) -> None:
    """Valida e escreve o contrato compartilhado e seus segmentos.

    ``payload`` tem a forma do doc devolvido por `read_indicator`. Escrevemos
    o dict tal como está (após validar) para não adicionar `scope` ao arquivo
    compartilhado nem reformatar campos que o usuário não tocou.
    """
    shared = payload.get('shared')
    if shared is not None:
        _validate_and_write(workspace, shared['path'], shared['config'])
    for segment in payload.get('segments', []):
        _validate_and_write(workspace, segment['path'], segment['config'])
