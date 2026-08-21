"""Loads and validates `categorias.yaml` — the declarative categoria->INMS
mapping used by the `split` step (spec §14.2). One file per orgao
(`configs/<orgao>/categorias.yaml`), since `Grupo_executor` literals differ
between MinC and MTur.
"""
from __future__ import annotations

from functools import cache
from pathlib import Path
from typing import Annotated, Final, Literal, Self, TypeAlias

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

__all__: Final[tuple[str, ...]] = (
    "CategoriaConfig",
    "CategoriaGrupoExecutor",
    "CategoriasFile",
    "GrupoExecutorMode",
    "WholeIndicatorMode",
    "load_categorias",
)

_StrictFrozen: Final[ConfigDict] = ConfigDict(
    frozen=True,
    strict=True,
    extra="forbid",
    str_strip_whitespace=True,
)


class GrupoExecutorMode(BaseModel):
    """A `mode: grupo_executor` entry — exactly one of `in_values` or
    `catch_all_contains` (resolved against the raw CSV at `split` runtime,
    not here)."""

    model_config = _StrictFrozen
    mode: Literal["grupo_executor"]
    # Bare list[str], not `ColumnIn` (models.py) — the YAML has no `column:`
    # key, `split` (ticket 03) supplies `column="Grupo_executor"` itself when
    # building the `ColumnIn` it actually filters rows with.
    in_values: list[str] | None = Field(default=None, min_length=1)
    catch_all_contains: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _check_exactly_one_filter(self) -> Self:
        has_in_values = self.in_values is not None
        has_catch_all = self.catch_all_contains is not None
        if has_in_values == has_catch_all:
            raise ValueError(
                "grupo_executor mode requires exactly one of 'in_values', 'catch_all_contains'"
            )
        return self


class WholeIndicatorMode(BaseModel):
    """A `mode: whole_indicator` entry — no filter, skips `split` entirely."""

    model_config = _StrictFrozen
    mode: Literal["whole_indicator"]


CategoriaGrupoExecutor: TypeAlias = Annotated[
    GrupoExecutorMode | WholeIndicatorMode, Field(discriminator="mode")
]


class CategoriaConfig(BaseModel):
    model_config = _StrictFrozen
    label: str = Field(min_length=1)
    inms: dict[str, CategoriaGrupoExecutor] = Field(min_length=1)


class CategoriasFile(BaseModel):
    """Root of a validated `categorias.yaml`."""

    model_config = _StrictFrozen
    categorias: dict[str, CategoriaConfig] = Field(min_length=1)


def _load_raw(path: Path) -> CategoriasFile:
    text = path.read_text(encoding="utf-8")
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValueError(f"malformed YAML in {path}: {exc}") from exc
    try:
        return CategoriasFile.model_validate(raw)
    except ValidationError as exc:
        raise ValueError(f"invalid categorias file {path}: {exc}") from exc


# Unbounded (vs. manifest.py's maxsize=1): one categorias.yaml per orgao,
# so the cache only ever holds a handful of entries.
@cache
def load_categorias(path: Path) -> CategoriasFile:
    """Load and cache a `categorias.yaml` from *path*.

    Raises:
        ValueError: if the YAML is malformed or fails schema validation.
        FileNotFoundError: if *path* does not exist.
    """
    return _load_raw(path)
