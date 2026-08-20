"""Loads and validates the dataset manifest (`datasets.yaml`).

The manifest maps human-readable dataset aliases (e.g. ``telefonemas``)
to concrete CSV filenames + parsing options.  Indicator YAMLs reference
datasets by alias via ``source.dataset``; the pipeline resolves the
alias to a real file at load time.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Final, Mapping

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

__all__: Final[tuple[str, ...]] = (
    "DatasetEntry",
    "DatasetManifest",
    "load_manifest",
)


class DatasetEntry(BaseModel):
    """A single dataset definition — immutable, strict."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    file: str
    delimiter: str = ";"
    encoding: str = "utf-8-sig"


class _RawManifest(dict[str, object]):
    """Typed wrapper for the raw YAML top-level mapping."""


class DatasetManifest:
    """Immutable registry of dataset entries, keyed by alias.

    Constructed once via :func:`load_manifest` and shared across the
    pipeline.  Lookup raises ``KeyError`` on unknown aliases.
    """

    def __init__(self, entries: Mapping[str, DatasetEntry]) -> None:
        self._entries: Final[Mapping[str, DatasetEntry]] = entries

    def resolve(self, alias: str) -> DatasetEntry:
        """Return the :class:`DatasetEntry` for *alias*.

        Raises:
            KeyError: if *alias* is not present in the manifest.
        """
        try:
            return self._entries[alias]
        except KeyError:
            available = ", ".join(sorted(self._entries))
            raise KeyError(
                f"dataset alias {alias!r} not found in manifest; "
                f"available: {available}"
            ) from None

    @property
    def aliases(self) -> tuple[str, ...]:
        return tuple(sorted(self._entries))


def _load_raw(path: Path) -> Mapping[str, DatasetEntry]:
    text = path.read_text(encoding="utf-8")
    raw = yaml.safe_load(text)
    if not isinstance(raw, dict) or "datasets" not in raw:
        raise ValueError("manifest YAML must be a mapping with a 'datasets' key")
    raw_datasets = raw["datasets"]
    if not isinstance(raw_datasets, dict):
        raise ValueError("'datasets' must be a mapping")
    entries: dict[str, DatasetEntry] = {}
    for alias, value in raw_datasets.items():
        if not isinstance(alias, str):
            raise ValueError(f"dataset alias must be a string, got {type(alias).__name__}")
        try:
            entry = DatasetEntry.model_validate(value)
        except ValidationError as exc:
            raise ValueError(f"invalid dataset entry {alias!r}: {exc}") from exc
        entries[alias] = entry
    return entries


@lru_cache(maxsize=1)
def load_manifest(path: Path) -> DatasetManifest:
    """Load and cache the dataset manifest from *path*.

    Raises:
        ValueError: if the YAML structure is invalid.
        FileNotFoundError: if *path* does not exist.
    """
    entries = _load_raw(path)
    return DatasetManifest(entries)
