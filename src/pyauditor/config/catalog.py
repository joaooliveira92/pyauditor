"""Loads the Anexo E catalog (106 itens) from `configs/anexo_e.yaml`.

Source is docs/termo_de_referencia/anexo_e_desconformidade_tecnica.html,
extracted to YAML at build time. See docs/spec/inms-pipeline.md §11.1.

Lives in `configs/` alongside every other YAML the pipeline reads (single
user, single checkout — no wheel/zipapp distribution to keep hermetic),
not packaged under `pyauditor.config.catalogs` anymore: that was the only
config file resolved via `importlib.resources` instead of a filesystem
path, an inconsistency with no real payoff here.
"""

from __future__ import annotations

from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import Final, TypedDict, TypeGuard, cast

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

__all__: Final[tuple[str, ...]] = ('CatalogItem', 'load_anexo_e_catalog')

# Matches cli/parser.py's `_DEFAULT_CONFIG_DIR` — resolved relative to CWD,
# same convention as every other config path in this app.
_CATALOG_PATH: Final[Path] = Path('configs/anexo_e.yaml')


class CatalogItem(BaseModel):
    """Single Anexo E item — immutable, strict."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        extra='forbid',
        str_strip_whitespace=True,
    )

    id: str
    categoria: str
    descricao: str
    referencia: str
    pontos: int


# TypedDict for the raw YAML shape — validated before Pydantic
class _RawItem(TypedDict):
    id: str
    categoria: str
    descricao: str
    referencia: str
    pontos: int


class _RawCatalog(TypedDict):
    items: list[_RawItem]


def _is_raw_catalog(obj: object) -> TypeGuard[_RawCatalog]:
    if not isinstance(obj, dict):
        return False
    items = obj.get('items')
    return isinstance(items, list)


def _read_catalog_text() -> str:
    try:
        return _CATALOG_PATH.read_text(encoding='utf-8')
    except OSError as exc:
        raise RuntimeError(
            f'failed to read catalog {_CATALOG_PATH}: {exc}'
        ) from exc


def _load_raw() -> _RawCatalog:
    text: str = _read_catalog_text()
    try:
        # yaml.safe_load has no stubs → Any. Isolate Any to one line.
        raw_any: object = cast(object, yaml.safe_load(text))
    except yaml.YAMLError as exc:
        raise ValueError(
            f'malformed YAML in catalog {_CATALOG_PATH}: {exc}'
        ) from exc
    if not _is_raw_catalog(raw_any):
        raise ValueError("catalog YAML must be mapping with 'items: list'")
    return raw_any


@lru_cache(maxsize=1)
def load_anexo_e_catalog() -> Mapping[str, CatalogItem]:
    """Load and validate Anexo E catalog — cached, immutable.

    Returns:
        Mapping from id -> CatalogItem (106 items). MappingProxyType prevents
        mutation of the cached instance.

    Raises:
        RuntimeError: if packaged YAML is missing/unreadable.
        ValueError: if YAML shape is invalid, malformed, or an item fails
            Pydantic validation (`ValidationError` is caught and re-raised
            as `ValueError` with the offending index).
    """
    raw: _RawCatalog = _load_raw()
    # raw["items"] is list[_RawItem] per TypeGuard, but each element is still
    # Any from YAML — validate via Pydantic strict mode.
    items: dict[str, CatalogItem] = {}
    for idx, raw_item in enumerate(raw['items']):
        try:
            item = CatalogItem.model_validate(raw_item)
        except ValidationError as exc:
            raise ValueError(
                f'invalid catalog item at index {idx}: {exc}'
            ) from exc
        if item.id in items:
            raise ValueError(f'duplicate catalog id: {item.id!r}')
        items[item.id] = item

    return MappingProxyType(items)  # immutable view over cached dict
