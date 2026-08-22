from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from pyauditor.config.manifest import DatasetEntry, DatasetManifest, load_manifest


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "datasets.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_load_manifest_resolves_alias(tmp_path: Path) -> None:
    load_manifest.cache_clear()
    path = _write(tmp_path, "datasets:\n  telefonemas:\n    file: telefonemas.csv\n")

    manifest = load_manifest(path)

    entry = manifest.resolve("telefonemas")
    assert entry.file == "telefonemas.csv"
    assert entry.delimiter == ";"
    assert entry.encoding == "utf-8-sig"
    assert manifest.aliases == ("telefonemas",)


def test_load_manifest_unknown_alias_raises_key_error(tmp_path: Path) -> None:
    load_manifest.cache_clear()
    path = _write(tmp_path, "datasets:\n  telefonemas:\n    file: telefonemas.csv\n")
    manifest = load_manifest(path)

    with pytest.raises(KeyError, match="unknown_alias"):
        manifest.resolve("unknown_alias")


def test_load_manifest_malformed_yaml_raises_actionable_value_error(tmp_path: Path) -> None:
    load_manifest.cache_clear()
    path = _write(tmp_path, "datasets:\n  telefonemas: [unclosed\n")

    with pytest.raises(ValueError, match="malformed YAML"):
        load_manifest(path)


def test_load_manifest_missing_datasets_key_raises(tmp_path: Path) -> None:
    load_manifest.cache_clear()
    path = _write(tmp_path, "not_datasets: {}\n")

    with pytest.raises(ValueError, match="datasets"):
        load_manifest(path)


def test_load_manifest_non_dict_datasets_raises(tmp_path: Path) -> None:
    load_manifest.cache_clear()
    path = _write(tmp_path, "datasets: not_a_mapping\n")

    with pytest.raises(ValueError, match="must be a mapping"):
        load_manifest(path)


def test_load_manifest_non_string_alias_raises(tmp_path: Path) -> None:
    load_manifest.cache_clear()
    path = _write(tmp_path, "datasets:\n  1:\n    file: x.csv\n")

    with pytest.raises(ValueError, match="alias must be a string"):
        load_manifest(path)


def test_load_manifest_invalid_entry_raises(tmp_path: Path) -> None:
    load_manifest.cache_clear()
    path = _write(tmp_path, 'datasets:\n  telefonemas:\n    file: ""\n')

    with pytest.raises(ValueError, match="invalid dataset entry"):
        load_manifest(path)


def test_load_manifest_caches_by_path(tmp_path: Path) -> None:
    load_manifest.cache_clear()
    path = _write(tmp_path, "datasets:\n  telefonemas:\n    file: telefonemas.csv\n")

    assert load_manifest(path) is load_manifest(path)


def test_dataset_entry_rejects_empty_fields() -> None:
    with pytest.raises(ValidationError):
        DatasetEntry(file="", delimiter="", encoding="")


def test_dataset_entry_rejects_path_traversal() -> None:
    with pytest.raises(ValidationError, match="must be a relative filename"):
        DatasetEntry(file="../../etc/passwd")


def test_dataset_entry_rejects_absolute_path() -> None:
    with pytest.raises(ValidationError, match="must be a relative filename"):
        DatasetEntry(file="/etc/passwd")


def test_dataset_manifest_resolve_error_lists_available_aliases() -> None:
    manifest = DatasetManifest({"a": DatasetEntry(file="a.csv")})

    with pytest.raises(KeyError, match="available: a"):
        manifest.resolve("b")
