"""Carrega e valida o manifest de datasets (`datasets.yaml`).

O manifest mapeia aliases legíveis (ex.: ``telefonemas``) para nomes de arquivo
CSV + opções de parsing. Os YAMLs de indicador referenciam datasets por alias
via ``source.dataset``; o pipeline resolve o alias para o arquivo real no load.
"""

from __future__ import annotations

from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Final

import yaml
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
)

from pyauditor.config._paths import reject_unsafe_relative_path

__all__: Final[tuple[str, ...]] = (
    'DatasetEntry',
    'DatasetManifest',
    'load_manifest',
)

type _SafeRelativePath = Annotated[
    str, AfterValidator(reject_unsafe_relative_path)
]


class DatasetEntry(BaseModel):
    """Uma única definição de dataset — imutável, estrita."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        extra='forbid',
        str_strip_whitespace=True,
    )

    file: _SafeRelativePath = Field(min_length=1)
    delimiter: str = Field(default=';', min_length=1)
    encoding: str = Field(default='utf-8-sig', min_length=1)


class DatasetManifest:
    """Registro imutável de entradas de dataset, indexado por alias.

    Construído uma vez via :func:`load_manifest` e compartilhado pelo
    pipeline. A consulta levanta ``KeyError`` em aliases desconhecidos.
    """

    def __init__(self, entries: Mapping[str, DatasetEntry]) -> None:
        self._entries: Final[Mapping[str, DatasetEntry]] = entries

    def resolve(self, alias: str) -> DatasetEntry:
        """Retorna o :class:`DatasetEntry` de *alias*.

        Raises:
            KeyError: se *alias* não estiver presente no manifest.
        """
        try:
            return self._entries[alias]
        except KeyError:
            available = ', '.join(sorted(self._entries))
            raise KeyError(
                f'dataset alias {alias!r} not found in manifest; available: '
                f'{available}'
            ) from None

    @property
    def aliases(self) -> tuple[str, ...]:
        return tuple(sorted(self._entries))


def _load_raw(path: Path) -> Mapping[str, DatasetEntry]:
    text = path.read_text(encoding='utf-8')
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValueError(f'malformed YAML in {path}: {exc}') from exc
    if not isinstance(raw, dict) or 'datasets' not in raw:
        raise ValueError(
            "manifest YAML must be a mapping with a 'datasets' key"
        )
    raw_datasets = raw['datasets']
    if not isinstance(raw_datasets, dict):
        raise ValueError("'datasets' must be a mapping")
    entries: dict[str, DatasetEntry] = {}
    for alias, value in raw_datasets.items():
        if not isinstance(alias, str):
            raise ValueError(
                f'dataset alias must be a string, got {type(alias).__name__}'
            )
        try:
            entry = DatasetEntry.model_validate(value)
        except ValidationError as exc:
            raise ValueError(f'invalid dataset entry {alias!r}: {exc}') from exc
        entries[alias] = entry
    return entries


@lru_cache(maxsize=1)
def load_manifest(path: Path) -> DatasetManifest:
    """Carrega e cacheia o manifest de datasets de *path*.

    Raises:
        ValueError: se a estrutura do YAML for inválida.
        FileNotFoundError: se *path* não existir.
    """
    entries = _load_raw(path)
    return DatasetManifest(entries)
