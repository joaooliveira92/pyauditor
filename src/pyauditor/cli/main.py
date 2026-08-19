"""CLI entry point. Subcommands per spec §6: `bootstrap` / `measure` / `report`.

All 3 are implemented: `bootstrap` (ticket 08), `measure` (ticket 03),
`report` (ticket 09).
"""
from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, NoReturn, TypeAlias, TypeGuard, TypeVar, assert_never, cast

from pyauditor.cli.bootstrap import run_bootstrap
from pyauditor.cli.measure import run_measure
from pyauditor.cli.report import run_report

__all__: Final[tuple[str, ...]] = ("MeasureRequest", "ReportRequest", "build_parser", "cli_main")

_PROG: Final[str] = "pyauditor"
_CMD_MEASURE: Final[Literal["measure"]] = "measure"
_CMD_BOOTSTRAP: Final[Literal["bootstrap"]] = "bootstrap"
_CMD_REPORT: Final[Literal["report"]] = "report"

Command: TypeAlias = Literal["measure", "bootstrap", "report"]

_DEFAULT_CONFIG_DIR: Final[Path] = Path("configs")
_DEFAULT_DATA_DIR: Final[Path] = Path("input")
_DEFAULT_OUTPUT_DIR: Final[Path] = Path("roms")
_DEFAULT_CAPA_PATH: Final[Path] = Path("capa.xlsx")
_DEFAULT_REPORT_DIR: Final[Path] = Path("reports")


@dataclass(frozen=True, slots=True)
class MeasureRequest:
    """Validated, immutable request for `measure`."""

    competencia: str
    config_dir: Path
    data_dir: Path
    output_dir: Path


@dataclass(frozen=True, slots=True)
class ReportRequest:
    """Validated, immutable request for `report`."""

    competencia: str
    capa_path: Path
    roms_dir: Path
    output_path: Path


def _is_command(value: str) -> TypeGuard[Command]:
    return value in (_CMD_MEASURE, _CMD_BOOTSTRAP, _CMD_REPORT)


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


def build_parser() -> argparse.ArgumentParser:
    """Build strictly-typed parser for spec §6."""
    parser = argparse.ArgumentParser(prog=_PROG)
    subparsers = parser.add_subparsers(dest="command", required=True)

    measure_parser = subparsers.add_parser(
        _CMD_MEASURE, help="apura os indicadores de uma competência"
    )
    measure_parser.add_argument("competencia", help='ex.: "2026-06"')
    measure_parser.add_argument(
        "--config-dir", type=Path, default=_DEFAULT_CONFIG_DIR
    )
    measure_parser.add_argument("--data-dir", type=Path, default=_DEFAULT_DATA_DIR)
    measure_parser.add_argument(
        "--output-dir", type=Path, default=_DEFAULT_OUTPUT_DIR
    )

    bootstrap_parser = subparsers.add_parser(
        _CMD_BOOTSTRAP, help="cria a capa Excel do contrato, se ainda não existir"
    )
    bootstrap_parser.add_argument("--capa-path", type=Path, default=_DEFAULT_CAPA_PATH)

    report_parser = subparsers.add_parser(
        _CMD_REPORT, help="consolida os ROMs de uma competência no Excel final"
    )
    report_parser.add_argument("competencia", help='ex.: "2026-06"')
    report_parser.add_argument("--capa-path", type=Path, default=_DEFAULT_CAPA_PATH)
    report_parser.add_argument("--roms-dir", type=Path, default=_DEFAULT_OUTPUT_DIR)
    report_parser.add_argument("--output-dir", type=Path, default=_DEFAULT_REPORT_DIR)

    return parser


def _extract_measure_request(ns: argparse.Namespace) -> MeasureRequest:
    return MeasureRequest(
        competencia=_require(ns, "competencia", str),
        config_dir=_require(ns, "config_dir", Path),
        data_dir=_require(ns, "data_dir", Path),
        output_dir=_require(ns, "output_dir", Path),
    )


def _extract_capa_path(ns: argparse.Namespace) -> Path:
    return _require(ns, "capa_path", Path)


def _extract_report_request(ns: argparse.Namespace) -> ReportRequest:
    competencia = _require(ns, "competencia", str)
    output_dir = _require(ns, "output_dir", Path)
    return ReportRequest(
        competencia=competencia,
        capa_path=_require(ns, "capa_path", Path),
        roms_dir=_require(ns, "roms_dir", Path),
        output_path=output_dir / f"relatorio_{competencia}.xlsx",
    )


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
        return run_measure(
            competencia=request.competencia,
            config_dir=request.config_dir,
            data_dir=request.data_dir,
            output_dir=request.output_dir,
        )
    elif command == _CMD_BOOTSTRAP:
        return run_bootstrap(_extract_capa_path(args))
    elif command == _CMD_REPORT:
        report_request = _extract_report_request(args)
        return run_report(
            competencia=report_request.competencia,
            capa_path=report_request.capa_path,
            roms_dir=report_request.roms_dir,
            output_path=report_request.output_path,
        )
    else:
        assert_never(command)


def _main() -> NoReturn:
    sys.exit(cli_main())


if __name__ == "__main__":
    _main()