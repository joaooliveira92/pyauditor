from __future__ import annotations

from pathlib import Path
from types import MappingProxyType
from typing import Mapping, assert_type
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from pyauditor.config.catalog import CatalogItem, load_anexo_e_catalog


def test_load_returns_mapping_and_is_cached() -> None:
    load_anexo_e_catalog.cache_clear()
    cat1 = load_anexo_e_catalog()
    cat2 = load_anexo_e_catalog()
    assert_type(cat1, Mapping[str, CatalogItem])
    assert cat1 is cat2  # lru_cache
    assert isinstance(cat1, MappingProxyType)
    assert len(cat1) == 106

def test_catalog_item_frozen() -> None:
    item = CatalogItem(id="E-001", categoria="X", descricao="d", referencia="r", pontos=1)
    with pytest.raises(ValidationError):
        CatalogItem(id="E-001", categoria="X", descricao="d", referencia="r", pontos="1")  # type: ignore[arg-type]  # strict
    with pytest.raises(Exception):
        item.pontos = 2  # frozen

def test_mutation_blocked() -> None:
    cat = load_anexo_e_catalog()
    with pytest.raises(TypeError):
        cat["new"] = CatalogItem(id="new", categoria="X", descricao="d", referencia="r", pontos=1)  # type: ignore[index]

def test_invalid_yaml_shape_raises(tmp_path: Path) -> None:
    load_anexo_e_catalog.cache_clear()
    with patch("pyauditor.config.catalog._read_catalog_text", return_value="not_a_catalog: true"):
        with pytest.raises(ValueError, match="mapping with 'items"):
            load_anexo_e_catalog()

def test_duplicate_id_raises() -> None:
    load_anexo_e_catalog.cache_clear()
    dup_yaml = "items:\n  - {id: E-001, categoria: X, descricao: d, referencia: r, pontos: 1}\n  - {id: E-001, categoria: X, descricao: d, referencia: r, pontos: 1}\n"
    with patch("pyauditor.config.catalog._read_catalog_text", return_value=dup_yaml):
        with pytest.raises(ValueError, match="duplicate"):
            load_anexo_e_catalog()