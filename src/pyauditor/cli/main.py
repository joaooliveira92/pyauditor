"""CLI entry point. Subcommands per spec §6: `bootstrap` / `measure` /
`report`, plus `consolidate` (2.1, .scratch/multi-org-pipeline map).

`bootstrap` (ticket 08), `measure` (ticket 03), `report` (ticket 09),
`consolidate` (multi-org-pipeline tickets 01/02/04) are all implemented.
"""
from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Final, Literal, NoReturn, TypeAlias, TypeGuard, TypeVar, assert_never, cast

from pyauditor.cli.bootstrap import run_bootstrap
from pyauditor.cli.consolidate import run_consolidate
from pyauditor.cli.measure import run_measure
from pyauditor.cli.report import run_report
from pyauditor.config.manifest import load_manifest
from pyauditor.logging import setup_logging

__all__: Final[tuple[str, ...]] = (
    "ConsolidateRequest", "MeasureRequest", "ReportRequest", "build_parser", "cli_main",
)

_PROG: Final[str] = "pyauditor"
_CMD_MEASURE: Final[Literal["measure"]] = "measure"
_CMD_BOOTSTRAP: Final[Literal["bootstrap"]] = "bootstrap"
_CMD_REPORT: Final[Literal["report"]] = "report"
_CMD_CONSOLIDATE: Final[Literal["consolidate"]] = "consolidate"

Command: TypeAlias = Literal["measure", "bootstrap", "report", "consolidate"]

Orgao: TypeAlias = Literal["MinC", "MTur", "both"]

_DEFAULT_CONFIG_DIR: Final[Path] = Path("configs")
_DEFAULT_DATA_DIR: Final[Path] = Path("input")
_DEFAULT_OUTPUT_DIR: Final[Path] = Path("roms")
_DEFAULT_CAPA_PATH: Final[Path] = Path("capa.xlsx")
_DEFAULT_REPORT_DIR: Final[Path] = Path("reports")
_SINGLE_ORGAOS: Final[tuple[str, str]] = ("MinC", "MTur")


@dataclass(frozen=True, slots=True)
class MeasureRequest:
    """Validated, immutable request for `measure`."""

    competencia: str
    config_dir: Path
    data_dir: Path
    output_dir: Path
    manifest_path: Path
    orgao: Orgao
    capa_path: Path


@dataclass(frozen=True, slots=True)
class ReportRequest:
    """Validated, immutable request for `report`."""

    competencia: str
    capa_path: Path
    roms_dir: Path
    output_path: Path
    config_dir: Path
    orgao: Orgao
    is_final_month: bool


@dataclass(frozen=True, slots=True)
class ConsolidateRequest:
    """Validated, immutable request for `consolidate` — CLI agnostic of
    `--orgao`: it's the MinC+MTur fusion step by definition (ticket 04 Q2).
    """

    competencia: str
    report_dir: Path
    roms_dir: Path
    output_path: Path


def _is_command(value: str) -> TypeGuard[Command]:
    return value in (_CMD_MEASURE, _CMD_BOOTSTRAP, _CMD_REPORT, _CMD_CONSOLIDATE)


_T = TypeVar("_T")


def _require(ns: argparse.Namespace, name: str, expected: type[_T]) -> _T:
    """Namespace attributes are `Any` by design — cast to `object` then
    narrow with isinstance. Confined to this boundary, argparse guarantees
    the attribute exists and has the type its `add_argument` declared.
    """
    value: object = cast(object, getattr(ns, name, None))
    if not isinstance(value, expected):
        raise TypeError(f"{name} must be {expected.__name__}")
    return value


def _add_orgao_argument(parser: argparse.ArgumentParser, *, default: Orgao = "MinC") -> None:
    parser.add_argument(
        "--orgao",
        type=str,
        choices=("MinC", "MTur", "both"),
        default=default,
        help="órgão da aferição (default: MinC). 'both' roda os dois, sequencial, sem cruzar",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build strictly-typed parser for spec §6."""
    parser = argparse.ArgumentParser(prog=_PROG)
    subparsers = parser.add_subparsers(dest="command", required=True)

    measure_parser = subparsers.add_parser(
        _CMD_MEASURE, help="apura os indicadores de uma competência"
    )
    measure_parser.add_argument("competencia", help='ex.: "2026-06"')
    _add_orgao_argument(measure_parser)
    measure_parser.add_argument(
        "--config-dir", type=Path, default=_DEFAULT_CONFIG_DIR
    )
    measure_parser.add_argument("--data-dir", type=Path, default=_DEFAULT_DATA_DIR)
    measure_parser.add_argument(
        "--output-dir", type=Path, default=_DEFAULT_OUTPUT_DIR
    )
    measure_parser.add_argument(
        "--manifest", type=Path, default=None,
        help="caminho para datasets.yaml (default: <config-dir>/<órgão>/datasets.yaml)"
    )
    measure_parser.add_argument("--capa-path", type=Path, default=None)

    bootstrap_parser = subparsers.add_parser(
        _CMD_BOOTSTRAP, help="cria a capa Excel do contrato, se ainda não existir"
    )
    _add_orgao_argument(bootstrap_parser)
    bootstrap_parser.add_argument("--capa-path", type=Path, default=None)

    report_parser = subparsers.add_parser(
        _CMD_REPORT, help="consolida os ROMs de uma competência no Excel final"
    )
    report_parser.add_argument("competencia", help='ex.: "2026-06"')
    _add_orgao_argument(report_parser)
    report_parser.add_argument("--capa-path", type=Path, default=None)
    report_parser.add_argument("--roms-dir", type=Path, default=_DEFAULT_OUTPUT_DIR)
    report_parser.add_argument("--output-dir", type=Path, default=_DEFAULT_REPORT_DIR)
    report_parser.add_argument(
        "--config-dir", type=Path, default=_DEFAULT_CONFIG_DIR
    )
    report_parser.add_argument(
        "--final-month",
        action="store_true",
        help="último mês de vigência do contrato — desliga o rollover de glosa (item 35 do TR)",
    )

    consolidate_parser = subparsers.add_parser(
        _CMD_CONSOLIDATE,
        help="funde os relatórios MinC+MTur já gerados na planilha financeira consolidada",
    )
    consolidate_parser.add_argument("competencia", help='ex.: "2026-06"')
    consolidate_parser.add_argument("--report-dir", type=Path, default=_DEFAULT_REPORT_DIR)
    consolidate_parser.add_argument("--roms-dir", type=Path, default=_DEFAULT_OUTPUT_DIR)

    return parser


def _extract_measure_request(ns: argparse.Namespace) -> MeasureRequest:
    config_dir = _require(ns, "config_dir", Path)
    orgao = _require(ns, "orgao", str)
    manifest_arg: object = cast(object, getattr(ns, "manifest", None))
    manifest_path = (
        config_dir / orgao / "datasets.yaml"
        if manifest_arg is None
        else _require(ns, "manifest", Path)
    )
    return MeasureRequest(
        competencia=_require(ns, "competencia", str),
        config_dir=config_dir,
        data_dir=_require(ns, "data_dir", Path),
        output_dir=_require(ns, "output_dir", Path),
        manifest_path=manifest_path,
        orgao=cast(Orgao, orgao),
        capa_path=_extract_capa_path(ns),
    )


def _extract_capa_path(ns: argparse.Namespace) -> Path:
    capa_arg: object = cast(object, getattr(ns, "capa_path", None))
    return capa_arg if isinstance(capa_arg, Path) else _DEFAULT_CAPA_PATH


def _capa_path_for(capa_path: Path, orgao: Orgao) -> Path:
    if capa_path != _DEFAULT_CAPA_PATH:
        return capa_path
    if orgao == "both":
        return _DEFAULT_CAPA_PATH
    return Path(f"capa_{orgao}.xlsx")


def _run_log_path(log_dir: Path, command: str, competencia: str | None = None) -> Path:
    """Timestamped per-run log file next to the command's outputs — every
    execution leaves a trace the user can consult to rastrear errors."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    suffix = f"-{competencia}" if competencia is not None else ""
    return log_dir / f"pyauditor-{command}{suffix}-{stamp}.log"


def _extract_report_request(ns: argparse.Namespace) -> ReportRequest:
    competencia = _require(ns, "competencia", str)
    output_dir = _require(ns, "output_dir", Path)
    orgao = _require(ns, "orgao", str)
    return ReportRequest(
        competencia=competencia,
        capa_path=_extract_capa_path(ns),
        roms_dir=_require(ns, "roms_dir", Path),
        output_path=output_dir / f"relatorio_{competencia}_{orgao}.xlsx",
        config_dir=_require(ns, "config_dir", Path),
        orgao=cast(Orgao, orgao),
        is_final_month=bool(cast(object, getattr(ns, "final_month", False))),
    )


def _extract_consolidate_request(ns: argparse.Namespace) -> ConsolidateRequest:
    competencia = _require(ns, "competencia", str)
    report_dir = _require(ns, "report_dir", Path)
    return ConsolidateRequest(
        competencia=competencia,
        report_dir=report_dir,
        roms_dir=_require(ns, "roms_dir", Path),
        output_path=report_dir / f"relatorio_{competencia}_consolidado.xlsx",
    )


def _each_single_orgao(orgao: str) -> tuple[str, ...]:
    return _SINGLE_ORGAOS if orgao == "both" else (orgao,)


def cli_main(argv: Sequence[str] | None = None) -> int:
    """Dispatch CLI. Returns exit code; never leaks Any."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # Boundary: Namespace.command is Any -> object -> str
    command_raw: object = cast(object, getattr(args, "command", None))
    if not isinstance(command_raw, str):
        parser.error("comando ausente")

    if not _is_command(command_raw):
        parser.error(f"comando desconhecido: {command_raw}")

    # Now narrowed to Command for exhaustive check
    command: Command = command_raw

    if command == _CMD_MEASURE:
        request = _extract_measure_request(args)
        setup_logging(
            log_path=_run_log_path(
                request.output_dir / request.orgao / request.competencia,
                _CMD_MEASURE, request.competencia,
            )
        )
        code = 0
        for orgao in _each_single_orgao(request.orgao):
            per_orgao_config_dir = request.config_dir / orgao
            per_orgao_data_dir = request.data_dir / orgao
            per_orgao_output_dir = request.output_dir / orgao
            per_orgao_manifest_path = request.config_dir / orgao / "datasets.yaml"
            per_orgao_capa = _capa_path_for(request.capa_path, cast(Orgao, orgao))
            manifest = None
            if per_orgao_manifest_path.exists():
                manifest = load_manifest(per_orgao_manifest_path)
            code |= run_measure(
                competencia=request.competencia,
                config_dir=per_orgao_config_dir,
                data_dir=per_orgao_data_dir,
                output_dir=per_orgao_output_dir,
                manifest=manifest,
                expected_orgao=orgao,
                capa_path=per_orgao_capa,
            )
        return code
    elif command == _CMD_BOOTSTRAP:
        capa_path = _extract_capa_path(args)
        orgao = _require(args, "orgao", str)
        code = 0
        for single_orgao in _each_single_orgao(orgao):
            per_orgao_capa = _capa_path_for(capa_path, cast(Orgao, single_orgao))
            setup_logging(log_path=_run_log_path(per_orgao_capa.parent, _CMD_BOOTSTRAP))
            code |= run_bootstrap(per_orgao_capa)
        return code
    elif command == _CMD_REPORT:
        report_request = _extract_report_request(args)
        setup_logging(
            log_path=_run_log_path(
                report_request.output_path.parent, _CMD_REPORT, report_request.competencia
            )
        )
        code = 0
        for orgao in _each_single_orgao(report_request.orgao):
            per_orgao_capa = _capa_path_for(report_request.capa_path, cast(Orgao, orgao))
            output_path = (
                report_request.output_path.parent
                / f"relatorio_{report_request.competencia}_{orgao}.xlsx"
            )
            code |= run_report(
                competencia=report_request.competencia,
                capa_path=per_orgao_capa,
                roms_dir=report_request.roms_dir / orgao,
                output_path=output_path,
                config_dir=report_request.config_dir / orgao,
                expected_orgao=orgao,
                is_final_month=report_request.is_final_month,
            )
        return code
    elif command == _CMD_CONSOLIDATE:
        consolidate_request = _extract_consolidate_request(args)
        setup_logging(
            log_path=_run_log_path(
                consolidate_request.output_path.parent, _CMD_CONSOLIDATE, consolidate_request.competencia
            )
        )
        return run_consolidate(
            competencia=consolidate_request.competencia,
            report_dir=consolidate_request.report_dir,
            roms_dir=consolidate_request.roms_dir,
            output_path=consolidate_request.output_path,
        )
    else:
        assert_never(command)


def _main() -> NoReturn:
    sys.exit(cli_main())


if __name__ == "__main__":
    _main()