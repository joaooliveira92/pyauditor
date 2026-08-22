"""Fronteira argparse→request: dataclasses imutáveis + tradutores validados
(ticket 01 SRP).

Extraído de `cli/main.py`: cada `*Request` e o `_extract_*_request`
correspondente
(mais `_require`, a validação de fronteira). Despacho multi-órgão e `cli_main`
continuam em `cli/main.py` — módulos sem import de volta para os comandos.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Final, TypedDict, cast

from pyauditor.cli.parser import _DEFAULT_DATA_DIR, Orgao
from pyauditor.config.resolution import resolve_manifest_path

__all__: Final[tuple[str, ...]] = (
    'ConsolidateRequest',
    'MeasureRequest',
    'ReportRequest',
    'SplitRequest',
    'extract_capa_path',
    'extract_consolidate_request',
    'extract_measure_request',
    'extract_report_request',
    'extract_split_request',
    'require',
)

# Migração das capas para CSV (ticket 07): o capa comum é `capa.csv`, as
# capas por órgão são `capa_{orgao}.csv` e o monetário vive em `objetos.csv`,
# todos sob `--data-dir` (default `input`). `--capa-path` sobrescreve apenas
# o capa comum; os por-órgão nunca ganham flag própria (Q6/Q9).
_CAPA_COMUM: Final[str] = 'capa.csv'
_OBJETOS_FILENAME: Final[str] = 'objetos.csv'


@dataclass(frozen=True, slots=True)
class MeasureRequest:
    """Validated, immutable request for `measure`."""

    competencia: str
    config_dir: Path
    data_dir: Path
    output_dir: Path
    manifest_path: Path
    orgao: Orgao
    strict: bool = False


@dataclass(frozen=True, slots=True)
class ReportRequest:
    """Validated, immutable request for `report`."""

    competencia: str
    capa_path: Path  # capa.csv comum (ticket 07 Q6/Q9)
    data_dir: Path  # onde vivem `capa_{orgao}.csv` e `objetos.csv`
    roms_dir: Path
    output_path: Path
    config_dir: Path
    orgao: Orgao
    is_final_month: bool


@dataclass(frozen=True, slots=True)
class SplitRequest:
    """Validated, immutable request for `split`."""

    competencia: str
    config_dir: Path
    data_dir: Path
    manifest_path: Path
    report_dir: Path
    orgao: Orgao
    strict: bool = False


@dataclass(frozen=True, slots=True)
class ConsolidateRequest:
    """Validated, immutable request for `consolidate` — CLI agnostic of
    `--orgao`: it's the MinC+MTur fusion step by definition (ticket 04 Q2).
    `data_dir` feeds `objetos.csv`, the monetary source (ticket 07).
    """

    competencia: str
    report_dir: Path
    roms_dir: Path
    output_path: Path
    data_dir: Path
    is_final_month: bool = False


class LoggingKwargs(TypedDict):
    """Flags de logging do argparse, com os tipos exatos que `setup_logging`
    espera — TypedDict para o unpacking `**` passar pelo basedpyright strict."""

    verbose: int
    log_level_explicit: str | None
    json_format: bool


def require[T](ns: argparse.Namespace, name: str, expected: type[T]) -> T:
    """Namespace attributes are `Any` by design — cast to `object` then
    narrow with isinstance. Confined to this boundary, argparse guarantees
    the attribute exists and has the type its `add_argument` declared.
    """
    value: object = cast(object, getattr(ns, name, None))
    if not isinstance(value, expected):
        raise TypeError(f'{name} must be {expected.__name__}')
    return value


def extract_strict(ns: argparse.Namespace) -> bool:
    return bool(cast(object, getattr(ns, 'strict', False)))


def logging_kwargs(args: argparse.Namespace) -> LoggingKwargs:
    """Translates argparse logging flags into `setup_logging` kwargs."""
    verbose = require(args, 'verbose', int)
    log_level_raw: object = cast(object, getattr(args, 'log_level', None))
    return {
        'verbose': verbose,
        'log_level_explicit': cast(str | None, log_level_raw),
        'json_format': cast(object, getattr(args, 'log_format', 'text'))
        == 'json',
    }


def extract_measure_request(ns: argparse.Namespace) -> MeasureRequest:
    config_dir = require(ns, 'config_dir', Path)
    data_dir = require(ns, 'data_dir', Path)
    orgao = require(ns, 'orgao', str)
    manifest_arg: object = cast(object, getattr(ns, 'manifest', None))
    manifest_path = (
        resolve_manifest_path(config_dir, orgao)
        if manifest_arg is None
        else require(ns, 'manifest', Path)
    )
    return MeasureRequest(
        competencia=require(ns, 'competencia', str),
        config_dir=config_dir,
        data_dir=data_dir,
        output_dir=require(ns, 'output_dir', Path),
        manifest_path=manifest_path,
        orgao=cast(Orgao, orgao),
        strict=extract_strict(ns),
    )


def extract_split_request(ns: argparse.Namespace) -> SplitRequest:
    config_dir = require(ns, 'config_dir', Path)
    orgao = require(ns, 'orgao', str)
    manifest_arg: object = cast(object, getattr(ns, 'manifest', None))
    manifest_path = (
        resolve_manifest_path(config_dir, orgao)
        if manifest_arg is None
        else require(ns, 'manifest', Path)
    )
    return SplitRequest(
        competencia=require(ns, 'competencia', str),
        config_dir=config_dir,
        data_dir=require(ns, 'data_dir', Path),
        manifest_path=manifest_path,
        report_dir=require(ns, 'report_dir', Path),
        orgao=cast(Orgao, orgao),
        strict=extract_strict(ns),
    )


def extract_capa_path(
    ns: argparse.Namespace, *, data_dir: Path | None = None
) -> Path:
    capa_arg: object = cast(object, getattr(ns, 'capa_path', None))
    if isinstance(capa_arg, Path):
        return capa_arg
    return (
        data_dir if data_dir is not None else _DEFAULT_DATA_DIR
    ) / _CAPA_COMUM


def extract_report_request(ns: argparse.Namespace) -> ReportRequest:
    competencia = require(ns, 'competencia', str)
    output_dir = require(ns, 'output_dir', Path)
    data_dir = require(ns, 'data_dir', Path)
    orgao = require(ns, 'orgao', str)
    return ReportRequest(
        competencia=competencia,
        capa_path=extract_capa_path(ns, data_dir=data_dir),
        data_dir=data_dir,
        roms_dir=require(ns, 'roms_dir', Path),
        output_path=output_dir / f'relatorio_{competencia}_{orgao}.xlsx',
        config_dir=require(ns, 'config_dir', Path),
        orgao=cast(Orgao, orgao),
        is_final_month=bool(cast(object, getattr(ns, 'final_month', False))),
    )


def extract_consolidate_request(ns: argparse.Namespace) -> ConsolidateRequest:
    competencia = require(ns, 'competencia', str)
    report_dir = require(ns, 'report_dir', Path)
    return ConsolidateRequest(
        competencia=competencia,
        report_dir=report_dir,
        roms_dir=require(ns, 'roms_dir', Path),
        output_path=report_dir / f'relatorio_{competencia}_consolidado.xlsx',
        data_dir=require(ns, 'data_dir', Path),
        is_final_month=bool(cast(object, getattr(ns, 'final_month', False))),
    )
