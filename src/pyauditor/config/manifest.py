"""Loads and validates the dataset manifest (`datasets.yaml`).

The manifest maps human-readable dataset aliases (e.g. ``telefonemas``)
to concrete CSV filenames + parsing options.  Indicator YAMLs reference
datasets by alias via ``source.dataset``; the pipeline resolves the
alias to a real file at load time.
"""

from __future__ import annotations

from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Final

import yaml
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, ValidationError

from pyauditor.config._paths import reject_unsafe_relative_path

__all__: Final[tuple[str, ...]] = (
    "DatasetEntry",
    "DatasetManifest",
    "load_manifest",
)

type _SafeRelativePath = Annotated[str, AfterValidator(reject_unsafe_relative_path)]


class DatasetEntry(BaseModel):
    """A single dataset definition — immutable, strict."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    file: _SafeRelativePath = Field(min_length=1)
    delimiter: str = Field(default=";", min_length=1)
    encoding: str = Field(default="utf-8-sig", min_length=1)


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
                f"dataset alias {alias!r} not found in manifest; available: {available}"
            ) from None

    @property
    def aliases(self) -> tuple[str, ...]:
        return tuple(sorted(self._entries))


def _load_raw(path: Path) -> Mapping[str, DatasetEntry]:
    text = path.read_text(encoding="utf-8")
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValueError(f"malformed YAML in {path}: {exc}") from exc
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
