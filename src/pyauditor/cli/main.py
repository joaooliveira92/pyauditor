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
from pathlib import Path
from typing import (
    Final,
    Literal,
    NoReturn,
    TypedDict,
    TypeGuard,
    assert_never,
    cast,
)

from pyauditor.cli.bootstrap import run_bootstrap
from pyauditor.cli.consolidate import check_consolidate_ready, run_consolidate
from pyauditor.cli.measure import _MeasuredIndicator, run_measure, write_combined_roms
from pyauditor.cli.report import ReportResult, check_report_ready, run_report
from pyauditor.cli.results import exit_code_for, exit_code_for_results
from pyauditor.cli.run import run_run
from pyauditor.cli.split import run_split
from pyauditor.config.manifest import load_manifest
from pyauditor.excel.equipe import EQUIPE_FILENAME
from pyauditor.logging import logger, setup_logging
from pyauditor.periodo import PeriodoAfericao, month_bounds

__all__: Final[tuple[str, ...]] = (
    "ConsolidateRequest",
    "MeasureRequest",
    "ReportRequest",
    "build_parser",
    "cli_main",
)

_PROG: Final[str] = "pyauditor"
_CMD_MEASURE: Final[Literal["measure"]] = "measure"
_CMD_BOOTSTRAP: Final[Literal["bootstrap"]] = "bootstrap"
_CMD_REPORT: Final[Literal["report"]] = "report"
_CMD_CONSOLIDATE: Final[Literal["consolidate"]] = "consolidate"
_CMD_SPLIT: Final[Literal["split"]] = "split"
_CMD_RUN: Final[Literal["run"]] = "run"

type Command = Literal["measure", "bootstrap", "report", "consolidate", "split", "run"]

type Orgao = Literal["MinC", "MTur", "both"]

_DEFAULT_CONFIG_DIR: Final[Path] = Path("configs")
_DEFAULT_DATA_DIR: Final[Path] = Path("input")
_DEFAULT_OUTPUT_DIR: Final[Path] = Path("roms")
_DEFAULT_CAPA_PATH: Final[Path] = Path("capa.xlsx")
_DEFAULT_REPORT_DIR: Final[Path] = Path("reports")
_SINGLE_ORGAOS: Final[tuple[str, str]] = ("MinC", "MTur")

# Migração das capas para CSV (ticket 07): o capa comum é `capa.csv`, as
# capas por órgão são `capa_{orgao}.csv` e o monetário vive em `objetos.csv`,
# todos sob `--data-dir` (default `input`). `--capa-path` sobrescreve apenas
# o capa comum; os por-órgão nunca ganham flag própria (Q6/Q9).
_CAPA_COMUM: Final[str] = "capa.csv"
_OBJETOS_FILENAME: Final[str] = "objetos.csv"


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


def _is_command(value: str) -> TypeGuard[Command]:
    return value in (
        _CMD_MEASURE,
        _CMD_BOOTSTRAP,
        _CMD_REPORT,
        _CMD_CONSOLIDATE,
        _CMD_SPLIT,
        _CMD_RUN,
    )


def _require[T](ns: argparse.Namespace, name: str, expected: type[T]) -> T:
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


_STRICT_HELP = (
    "descarta linhas sem prova de período (célula vazia ou formato "
    "desconhecido) em vez de mantê-las para os quality gates"
)


def _add_strict_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--strict", action="store_true", help=_STRICT_HELP)


def _extract_strict(ns: argparse.Namespace) -> bool:
    return bool(cast(object, getattr(ns, "strict", False)))


def _add_logging_arguments(parser: argparse.ArgumentParser) -> None:
    """Flags de observabilidade (ticket 05): verbosidade `-v`/`-vv`, nível
    explícito e formato JSON para automação. Aplicado a todos os subcomandos
    (Q8): o nível efetivo = `--log-level` se dado, senão a verbosidade."""
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="-v: um evento por indicador; -vv: detalhes de leitura/validação/cálculo",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        default=None,
        help="nível de log manual (prevalece sobre -v; default INFO)",
    )
    parser.add_argument(
        "--log-format",
        type=str,
        choices=("text", "json"),
        default="text",
        help="json: cada registro em stderr vira uma linha JSON ({time, level, event, ...})",
    )


class _LoggingKwargs(TypedDict):
    """Flags de logging do argparse, com os tipos exatos que `setup_logging`
    espera — TypedDict para o unpacking `**` passar pelo mypy strict."""

    verbose: int
    log_level_explicit: str | None
    json_format: bool


def _logging_kwargs(args: argparse.Namespace) -> _LoggingKwargs:
    """Traduz os flags de logging do argparse para `setup_logging`."""
    verbose = _require(args, "verbose", int)
    log_level_raw: object = cast(object, getattr(args, "log_level", None))
    return {
        "verbose": verbose,
        "log_level_explicit": cast(str | None, log_level_raw),
        "json_format": cast(object, getattr(args, "log_format", "text")) == "json",
    }


def build_parser() -> argparse.ArgumentParser:
    """Build strictly-typed parser for spec §6."""
    parser = argparse.ArgumentParser(prog=_PROG)
    subparsers = parser.add_subparsers(dest="command", required=True)

    measure_parser = subparsers.add_parser(
        _CMD_MEASURE, help="apura os indicadores de uma competência"
    )
    measure_parser.add_argument("competencia", help='ex.: "2026-06"')
    _add_orgao_argument(measure_parser)
    measure_parser.add_argument("--config-dir", type=Path, default=_DEFAULT_CONFIG_DIR)
    measure_parser.add_argument("--data-dir", type=Path, default=_DEFAULT_DATA_DIR)
    measure_parser.add_argument("--output-dir", type=Path, default=_DEFAULT_OUTPUT_DIR)
    measure_parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="caminho para datasets.yaml (default: <config-dir>/<órgão>/datasets.yaml)",
    )
    _add_strict_argument(measure_parser)
    _add_logging_arguments(measure_parser)

    bootstrap_parser = subparsers.add_parser(
        _CMD_BOOTSTRAP,
        help="cria as capas CSV do contrato (comum + por órgão), se ainda não existirem",
    )
    _add_orgao_argument(bootstrap_parser)
    bootstrap_parser.add_argument(
        "--data-dir",
        type=Path,
        default=_DEFAULT_DATA_DIR,
        help=f"onde criar capa.csv e capa_{{orgao}}.csv (default: {_DEFAULT_DATA_DIR})",
    )
    bootstrap_parser.add_argument(
        "--capa-path",
        type=Path,
        default=None,
        help="caminho do capa comum (cap.csv); default: <data-dir>/capa.csv",
    )
    _add_logging_arguments(bootstrap_parser)

    report_parser = subparsers.add_parser(
        _CMD_REPORT, help="consolida os ROMs de uma competência no Excel final"
    )
    report_parser.add_argument("competencia", help='ex.: "2026-06"')
    _add_orgao_argument(report_parser)
    report_parser.add_argument(
        "--data-dir",
        type=Path,
        default=_DEFAULT_DATA_DIR,
        help="onde vivem capa_{orgao}.csv e objetos.csv (default: input)",
    )
    report_parser.add_argument(
        "--capa-path",
        type=Path,
        default=None,
        help="caminho do capa comum capa.csv (default: <data-dir>/capa.csv)",
    )
    report_parser.add_argument("--roms-dir", type=Path, default=_DEFAULT_OUTPUT_DIR)
    report_parser.add_argument("--output-dir", type=Path, default=_DEFAULT_REPORT_DIR)
    report_parser.add_argument("--config-dir", type=Path, default=_DEFAULT_CONFIG_DIR)
    report_parser.add_argument(
        "--final-month",
        action="store_true",
        help="último mês de vigência do contrato — desliga o rollover de glosa (item 35 do TR)",
    )
    _add_logging_arguments(report_parser)

    consolidate_parser = subparsers.add_parser(
        _CMD_CONSOLIDATE,
        help="funde os relatórios MinC+MTur já gerados na planilha financeira consolidada",
    )
    consolidate_parser.add_argument("competencia", help='ex.: "2026-06"')
    consolidate_parser.add_argument("--report-dir", type=Path, default=_DEFAULT_REPORT_DIR)
    consolidate_parser.add_argument("--roms-dir", type=Path, default=_DEFAULT_OUTPUT_DIR)
    consolidate_parser.add_argument(
        "--data-dir",
        type=Path,
        default=_DEFAULT_DATA_DIR,
        help="onde vive objetos.csv, a fonte do valor mensal (default: input)",
    )
    _add_logging_arguments(consolidate_parser)

    split_parser = subparsers.add_parser(
        _CMD_SPLIT,
        help="gera CSVs filtrados + configs derivadas por Categoria (spec §14.3)",
    )
    split_parser.add_argument("competencia", help='ex.: "2026-06"')
    _add_orgao_argument(split_parser)
    split_parser.add_argument("--config-dir", type=Path, default=_DEFAULT_CONFIG_DIR)
    split_parser.add_argument("--data-dir", type=Path, default=_DEFAULT_DATA_DIR)
    split_parser.add_argument("--report-dir", type=Path, default=_DEFAULT_REPORT_DIR)
    split_parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="caminho para datasets.yaml (default: <config-dir>/<órgão>/datasets.yaml)",
    )
    _add_strict_argument(split_parser)
    _add_logging_arguments(split_parser)

    run_parser = subparsers.add_parser(
        _CMD_RUN,
        help="encadeia bootstrap→measure→report→consolidate numa invocação scriptável",
    )
    run_parser.add_argument("competencia", help='ex.: "2026-06"')
    _add_orgao_argument(run_parser)
    run_parser.add_argument("--config-dir", type=Path, default=_DEFAULT_CONFIG_DIR)
    run_parser.add_argument("--data-dir", type=Path, default=_DEFAULT_DATA_DIR)
    run_parser.add_argument("--output-dir", type=Path, default=_DEFAULT_OUTPUT_DIR)
    run_parser.add_argument("--report-dir", type=Path, default=_DEFAULT_REPORT_DIR)
    run_parser.add_argument("--capa-path", type=Path, default=None)
    _add_strict_argument(run_parser)
    run_parser.add_argument(
        "--output",
        type=str,
        choices=("text", "json"),
        default="text",
        help="formato do resumo final: 'text' (painel rico, padrão) ou 'json' (automação/CI)",
    )
    _add_logging_arguments(run_parser)
    run_parser.add_argument(
        "--final-month",
        action="store_true",
        help="último mês de vigência do contrato — desliga o rollover de glosa (item 35 do TR)",
    )
    run_parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "reprocessa tudo, mesmo etapas já concluídas numa tentativa anterior "
            "(default: retoma de onde parou, pulando o que já está 'done')"
        ),
    )

    return parser


def _extract_measure_request(ns: argparse.Namespace) -> MeasureRequest:
    config_dir = _require(ns, "config_dir", Path)
    data_dir = _require(ns, "data_dir", Path)
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
        data_dir=data_dir,
        output_dir=_require(ns, "output_dir", Path),
        manifest_path=manifest_path,
        orgao=cast(Orgao, orgao),
        strict=_extract_strict(ns),
    )


def _extract_split_request(ns: argparse.Namespace) -> SplitRequest:
    config_dir = _require(ns, "config_dir", Path)
    orgao = _require(ns, "orgao", str)
    manifest_arg: object = cast(object, getattr(ns, "manifest", None))
    manifest_path = (
        config_dir / orgao / "datasets.yaml"
        if manifest_arg is None
        else _require(ns, "manifest", Path)
    )
    return SplitRequest(
        competencia=_require(ns, "competencia", str),
        config_dir=config_dir,
        data_dir=_require(ns, "data_dir", Path),
        manifest_path=manifest_path,
        report_dir=_require(ns, "report_dir", Path),
        orgao=cast(Orgao, orgao),
        strict=_extract_strict(ns),
    )


def _extract_capa_path(ns: argparse.Namespace, *, data_dir: Path | None = None) -> Path:
    capa_arg: object = cast(object, getattr(ns, "capa_path", None))
    if isinstance(capa_arg, Path):
        return capa_arg
    return (data_dir if data_dir is not None else _DEFAULT_DATA_DIR) / _CAPA_COMUM


def _capa_path_for(capa_path: Path, orgao: Orgao) -> Path:
    """Delegates to ``pyauditor.capa_paths.resolve_capa_path`` — single
    implementation shared with ``orchestration/run.py`` (issue 05)."""
    from pyauditor.capa_paths import resolve_capa_path

    return resolve_capa_path(capa_path, orgao)


def _run_log_path(log_dir: Path, command: str, competencia: str | None = None) -> Path:
    """Timestamped per-run log file next to the command's outputs — every
    execution leaves a trace the user can consult to rastrear errors.

    O timestamp usa o placeholder `{time:...}` do próprio loguru (em vez de
    `datetime.now()` embutido no nome) porque a política de `retention` do
    logger (`pyauditor.logging._LOG_RETENTION`) só reconhece e limpa arquivos
    irmãos mais antigos quando consegue extrair o padrão glob a partir desse
    placeholder — um timestamp já resolvido no nome do arquivo é invisível
    para ela, e os logs se acumulariam indefinidamente."""
    suffix = f"-{competencia}" if competencia is not None else ""
    return log_dir / f"pyauditor-{command}{suffix}-{{time:YYYYMMDD-HHmmss}}.log"


def _extract_report_request(ns: argparse.Namespace) -> ReportRequest:
    competencia = _require(ns, "competencia", str)
    output_dir = _require(ns, "output_dir", Path)
    data_dir = _require(ns, "data_dir", Path)
    orgao = _require(ns, "orgao", str)
    return ReportRequest(
        competencia=competencia,
        capa_path=_extract_capa_path(ns, data_dir=data_dir),
        data_dir=data_dir,
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
        data_dir=_require(ns, "data_dir", Path),
    )


def _resolve_config_dir(base: Path, orgao: str) -> Path:
    """Single-source: se `base/_shared` existe, usa o canônico; senão fallback per-órgão."""
    shared = base / "_shared"
    if shared.is_dir():
        return shared
    return base / orgao


def _resolve_manifest_path(base: Path, orgao: str) -> Path:
    shared = base / "_shared" / "datasets.yaml"
    if shared.exists():
        return shared
    return base / orgao / "datasets.yaml"


def _each_single_orgao(orgao: str) -> tuple[str, ...]:
    return _SINGLE_ORGAOS if orgao == "both" else (orgao,)


def _dispatch_measure(args: argparse.Namespace) -> int:
    from pyauditor.cli.results import validate_competencia

    request = _extract_measure_request(args)
    if (msg := validate_competencia(request.competencia)) is not None:
        print(msg, file=sys.stderr)
        return 2
    # §2 — a janela da competência é derivada uma vez do argumento validado e
    # repassada a todos os órgãos; equipe.csv vive na raiz de --data-dir (§6),
    # não no diretório por órgão dos datasets.
    periodo: PeriodoAfericao = month_bounds(request.competencia)
    equipe_path = request.data_dir / EQUIPE_FILENAME
    setup_logging(
        log_path=_run_log_path(
            request.output_dir / request.orgao / request.competencia,
            _CMD_MEASURE,
            request.competencia,
        ),
        **_logging_kwargs(args),
    )
    measure_results = []
    per_orgao: dict[str, list[_MeasuredIndicator]] = {}
    for orgao in _each_single_orgao(request.orgao):
        per_orgao_config_dir = _resolve_config_dir(request.config_dir, orgao)
        per_orgao_data_dir = request.data_dir / orgao
        per_orgao_output_dir = request.output_dir / orgao
        per_orgao_manifest_path = _resolve_manifest_path(request.config_dir, orgao)
        manifest = None
        if per_orgao_manifest_path.exists():
            manifest = load_manifest(per_orgao_manifest_path)
        collect: list[_MeasuredIndicator] = []
        measure_results.append(
            run_measure(
                competencia=request.competencia,
                config_dir=per_orgao_config_dir,
                data_dir=per_orgao_data_dir,
                output_dir=per_orgao_output_dir,
                manifest=manifest,
                expected_orgao=orgao,
                equipe_path=equipe_path,
                periodo=periodo,
                strict=request.strict,
                collect=collect,
            )
        )
        per_orgao[orgao] = collect
    if request.orgao == "both":
        # Single markdown per indicator covering both orgãos, alongside the
        # per-orgão ROMs (roms/MinC/..., roms/MTur/...).
        write_combined_roms(per_orgao, request.competencia, request.output_dir, periodo=periodo)
    return exit_code_for_results(measure_results)


def _dispatch_split(args: argparse.Namespace) -> int:
    from pyauditor.cli.results import validate_competencia

    request = _extract_split_request(args)
    if (msg := validate_competencia(request.competencia)) is not None:
        print(msg, file=sys.stderr)
        return 2
    # Log fica junto dos artefatos _split (issue 11), não em data_dir/<orgao>/<competencia>
    # e sem pasta órfã "both"
    year, month = request.competencia.split("-")
    periodo: PeriodoAfericao = month_bounds(request.competencia)
    split_results = []
    for orgao in _each_single_orgao(request.orgao):
        # setup por órgão dentro do loop para evitar pasta both/ órfã
        setup_logging(
            log_path=_run_log_path(
                request.data_dir / orgao / year / month / "_split",
                _CMD_SPLIT,
                request.competencia,
            ),
            **_logging_kwargs(args),
        )
        per_orgao_config_dir = _resolve_config_dir(request.config_dir, orgao)
        per_orgao_data_dir = request.data_dir / orgao
        per_orgao_manifest_path = _resolve_manifest_path(request.config_dir, orgao)
        manifest = None
        if per_orgao_manifest_path.exists():
            manifest = load_manifest(per_orgao_manifest_path)
        split_results.append(
            run_split(
                competencia=request.competencia,
                config_dir=per_orgao_config_dir,
                data_dir=per_orgao_data_dir,
                expected_orgao=orgao,
                manifest=manifest,
                report_dir=request.report_dir / orgao,
                periodo=periodo,
                strict=request.strict,
            )
        )
    return exit_code_for_results(split_results)


def _dispatch_bootstrap(args: argparse.Namespace) -> int:
    data_dir = _require(args, "data_dir", Path)
    capa_path = _extract_capa_path(args, data_dir=data_dir)
    orgao = _require(args, "orgao", str)
    # bootstrap não tem competencia, nada a validar previamente
    bootstrap_results = []
    for single_orgao in _each_single_orgao(orgao):
        per_orgao_capa = _capa_path_for(capa_path, cast(Orgao, single_orgao))
        setup_logging(
            log_path=_run_log_path(per_orgao_capa.parent, _CMD_BOOTSTRAP),
            **_logging_kwargs(args),
        )
        bootstrap_results.append(run_bootstrap(per_orgao_capa, single_orgao))
    return exit_code_for_results(bootstrap_results)


def _dispatch_report(args: argparse.Namespace) -> int:
    from pyauditor.cli.results import validate_competencia

    report_request = _extract_report_request(args)
    if (msg := validate_competencia(report_request.competencia)) is not None:
        print(msg, file=sys.stderr)
        return 2
    setup_logging(
        log_path=_run_log_path(
            report_request.output_path.parent, _CMD_REPORT, report_request.competencia
        ),
        **_logging_kwargs(args),
    )
    report_results = []
    for orgao in _each_single_orgao(report_request.orgao):
        output_path = (
            report_request.output_path.parent
            / f"relatorio_{report_request.competencia}_{orgao}.xlsx"
        )
        # Pre-flight (ticket "Dependency enforcement"): same checker `run_report`
        # calls internally — fast, actionable error before touching the pipeline.
        per_orgao_roms_dir = report_request.roms_dir / orgao
        dependency_check = check_report_ready(
            report_request.competencia,
            orgao,
            report_request.capa_path,
            per_orgao_roms_dir,
            data_dir=report_request.data_dir,
        )
        if not dependency_check.satisfied:
            message = "dependência não satisfeita: " + "; ".join(dependency_check.missing)
            logger.error(message)
            report_results.append(
                ReportResult(
                    status="error",
                    competencia=report_request.competencia,
                    orgao=orgao,
                    output_path=output_path,
                    indicator_count=0,
                    warnings=(),
                    error_message=message,
                )
            )
            continue
        report_results.append(
            run_report(
                competencia=report_request.competencia,
                capa_path=report_request.capa_path,
                roms_dir=per_orgao_roms_dir,
                output_path=output_path,
                config_dir=_resolve_config_dir(report_request.config_dir, orgao),
                expected_orgao=orgao,
                is_final_month=report_request.is_final_month,
                data_dir=report_request.data_dir,
            )
        )
    return exit_code_for_results(report_results)


def _dispatch_consolidate(args: argparse.Namespace) -> int:
    from pyauditor.cli.results import validate_competencia

    consolidate_request = _extract_consolidate_request(args)
    if (msg := validate_competencia(consolidate_request.competencia)) is not None:
        print(msg, file=sys.stderr)
        return 2
    setup_logging(
        log_path=_run_log_path(
            consolidate_request.output_path.parent,
            _CMD_CONSOLIDATE,
            consolidate_request.competencia,
        ),
        **_logging_kwargs(args),
    )
    # Pre-flight (ticket "Dependency enforcement"): same checker `run_consolidate`
    # calls internally — fast, actionable error before touching the pipeline.
    dependency_check = check_consolidate_ready(
        consolidate_request.competencia,
        consolidate_request.report_dir,
        consolidate_request.roms_dir,
    )
    if not dependency_check.satisfied:
        message = "dependência não satisfeita: " + "; ".join(dependency_check.missing)
        logger.error(message)
        return exit_code_for("error")
    consolidate_result = run_consolidate(
        competencia=consolidate_request.competencia,
        report_dir=consolidate_request.report_dir,
        roms_dir=consolidate_request.roms_dir,
        output_path=consolidate_request.output_path,
        data_dir=consolidate_request.data_dir,
    )
    return exit_code_for_results((consolidate_result,))


def _dispatch_run(args: argparse.Namespace) -> int:
    from pyauditor.cli.results import validate_competencia

    competencia = _require(args, "competencia", str)
    if (msg := validate_competencia(competencia)) is not None:
        print(msg, file=sys.stderr)
        return 2
    orgao = _require(args, "orgao", str)
    output_dir = _require(args, "output_dir", Path)
    report_dir = _require(args, "report_dir", Path)
    setup_logging(
        log_path=_run_log_path(report_dir, _CMD_RUN, competencia),
        **_logging_kwargs(args),
    )
    output_raw = _require(args, "output", str)
    return run_run(
        competencia=competencia,
        orgao=orgao,
        config_dir=_require(args, "config_dir", Path),
        data_dir=_require(args, "data_dir", Path),
        output_dir=output_dir,
        report_dir=report_dir,
        capa_path=_extract_capa_path(args, data_dir=_require(args, "data_dir", Path)),
        final_month=bool(cast(object, getattr(args, "final_month", False))),
        output="json" if output_raw == "json" else "text",
        force=bool(cast(object, getattr(args, "force", False))),
        strict=_extract_strict(args),
    )


def cli_main(argv: Sequence[str] | None = None) -> int:
    """Dispatch CLI. Returns exit code; never leaks Any."""
    effective_argv = list(argv) if argv is not None else sys.argv[1:]

    if not effective_argv:
        # No args at all -> guided flow (map.md decision). A named command with
        # missing required args still falls through to argparse's normal error.
        if not sys.stdin.isatty():
            print(
                "nenhum terminal detectado — use um subcomando diretamente, "
                "ex.: `pyauditor measure 2026-06`",
                file=sys.stderr,
            )
            return 2
        from pyauditor.interactive import run_interactive  # local: TTY-gated import

        return run_interactive()

    parser = build_parser()
    args = parser.parse_args(effective_argv)

    # Boundary: Namespace.command is Any -> object -> str
    command_raw: object = cast(object, getattr(args, "command", None))
    if not isinstance(command_raw, str):
        parser.error("comando ausente")

    if not _is_command(command_raw):
        parser.error(f"comando desconhecido: {command_raw}")

    # Now narrowed to Command for exhaustive check
    command: Command = command_raw

    if command == _CMD_MEASURE:
        return _dispatch_measure(args)
    elif command == _CMD_BOOTSTRAP:
        return _dispatch_bootstrap(args)
    elif command == _CMD_REPORT:
        return _dispatch_report(args)
    elif command == _CMD_CONSOLIDATE:
        return _dispatch_consolidate(args)
    elif command == _CMD_SPLIT:
        return _dispatch_split(args)
    elif command == _CMD_RUN:
        return _dispatch_run(args)
    else:
        assert_never(command)


def _main() -> NoReturn:
    sys.exit(cli_main())


if __name__ == "__main__":
    _main()
