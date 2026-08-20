"""Loads the Anexo E catalog (106 itens) from packaged YAML.

Source is docs/termo_de_referencia/anexo_e_desconformidade_tecnica.html,
extracted to YAML at build time. See docs/spec/inms-pipeline.md §11.1.
"""
from __future__ import annotations

import importlib.resources
from functools import lru_cache
from types import MappingProxyType
from typing import Final, Mapping, TypedDict, TypeGuard, cast

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

__all__: Final[tuple[str, ...]] = ("CatalogItem", "load_anexo_e_catalog")

_CATALOG_PACKAGE: Final[str] = "pyauditor.config.catalogs"
_CATALOG_NAME: Final[str] = "anexo_e.yaml"


class CatalogItem(BaseModel):
    """Single Anexo E item — immutable, strict."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        extra="forbid",
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
    items = obj.get("items")
    return isinstance(items, list)


def _read_catalog_text() -> str:
    # Hermetic: importlib.resources works in wheel, zipapp, Bazel runfiles
    traversable = importlib.resources.files(_CATALOG_PACKAGE) / _CATALOG_NAME
    try:
        # Traversable.read_text is available in 3.11+, fallback to as_file
        if hasattr(traversable, "read_text"):
            return traversable.read_text(encoding="utf-8")
        with importlib.resources.as_file(traversable) as path:
            return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"failed to read packaged catalog {_CATALOG_NAME}: {exc}") from exc


def _load_raw() -> _RawCatalog:
    text: str = _read_catalog_text()
    try:
        # yaml.safe_load has no stubs → Any. Isolate Any to one line.
        raw_any: object = cast(object, yaml.safe_load(text))
    except yaml.YAMLError as exc:
        raise ValueError(f"malformed YAML in packaged catalog {_CATALOG_NAME}: {exc}") from exc
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
    for idx, raw_item in enumerate(raw["items"]):
        try:
            item = CatalogItem.model_validate(raw_item)
        except ValidationError as exc:
            raise ValueError(f"invalid catalog item at index {idx}: {exc}") from exc
        if item.id in items:
            raise ValueError(f"duplicate catalog id: {item.id!r}")
        items[item.id] = item

    return MappingProxyType(items)  # immutable view over cached dict