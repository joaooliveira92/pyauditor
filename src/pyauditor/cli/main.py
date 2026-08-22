"""CLI entry point. Subcommands per spec §6: `bootstrap` / `measure` /
`report`, plus `consolidate` (2.1, .scratch/multi-org-pipeline map) and
`split`/`run`.

Após o split SRP (ticket 01): o schema do parser vive em `cli/parser.py`, a
tradução argparse→request em `cli/requests.py` — este módulo fica com o
`cli_main` e o dispatch multi-órgão.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Final, NoReturn, TypeGuard, assert_never, cast

from pyauditor.capa_paths import resolve_capa_path
from pyauditor.cli.bootstrap import run_bootstrap
from pyauditor.cli.consolidate import run_consolidate
from pyauditor.cli.measure import (
    _MeasuredIndicator,
    run_measure,
    write_combined_roms,
)
from pyauditor.cli.parser import (
    _CMD_BOOTSTRAP,
    _CMD_CONSOLIDATE,
    _CMD_MEASURE,
    _CMD_REPORT,
    _CMD_RUN,
    _CMD_SPLIT,
    Command,
    Orgao,
    build_parser,
)
from pyauditor.cli.report import run_report
from pyauditor.cli.requests import (
    _CAPA_COMUM,
    ConsolidateRequest,
    MeasureRequest,
    ReportRequest,
    extract_capa_path,
    extract_consolidate_request,
    extract_measure_request,
    extract_report_request,
    extract_split_request,
    logging_kwargs,
    require,
)
from pyauditor.cli.results import exit_code_for_results
from pyauditor.cli.run import run_run
from pyauditor.cli.split import run_split
from pyauditor.config.resolution import per_orgao_paths
from pyauditor.excel.equipe import EQUIPE_FILENAME
from pyauditor.excel.prazos import PRAZOS_FILENAME
from pyauditor.logging import setup_logging
from pyauditor.periodo import PeriodoAfericao, month_bounds

__all__: Final[tuple[str, ...]] = (
    'ConsolidateRequest',
    'MeasureRequest',
    'ReportRequest',
    'build_parser',
    'cli_main',
    'main',
)

# Migração das capas para CSV (ticket 07): o monetário vive em `objetos.csv`.
_OBJETOS_FILENAME: Final[str] = 'objetos.csv'

_SINGLE_ORGAOS: Final[tuple[str, str]] = ('MinC', 'MTur')


def _is_command(value: str) -> TypeGuard[Command]:
    return value in (
        _CMD_MEASURE,
        _CMD_BOOTSTRAP,
        _CMD_REPORT,
        _CMD_CONSOLIDATE,
        _CMD_SPLIT,
        _CMD_RUN,
    )


def _run_log_path(
    log_dir: Path, command: str, competencia: str | None = None
) -> Path:
    """Timestamped per-run log file next to the command's outputs — every
    execution leaves a trace the user can consult to rastrear errors.

    O timestamp usa o placeholder `{time:...}` do próprio loguru (em vez de
    `datetime.now()` embutido no nome) porque a política de `retention` do
    logger (`pyauditor.logging._LOG_RETENTION`) só reconhece e limpa arquivos
    irmãos mais antigos quando consegue extrair o padrão glob a partir desse
    placeholder — um timestamp já resolvido no nome do arquivo é invisível
    para ela, e os logs se acumulariam indefinidamente."""
    suffix = f'-{competencia}' if competencia is not None else ''
    return log_dir / f'pyauditor-{command}{suffix}-{{time:YYYYMMDD-HHmmss}}.log'


def _each_single_orgao(orgao: str) -> tuple[str, ...]:
    return _SINGLE_ORGAOS if orgao == 'both' else (orgao,)


def _dispatch_measure(args: argparse.Namespace) -> int:
    from pyauditor.cli.results import validate_competencia

    request = extract_measure_request(args)
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
        **logging_kwargs(args),
    )
    measure_results = []
    per_orgao: dict[str, list[_MeasuredIndicator]] = {}
    for orgao in _each_single_orgao(request.orgao):
        paths = per_orgao_paths(
            config_dir=request.config_dir,
            data_dir=request.data_dir,
            output_dir=request.output_dir,
            orgao=orgao,
        )
        collect: list[_MeasuredIndicator] = []
        measure_results.append(
            run_measure(
                competencia=request.competencia,
                config_dir=paths.config_dir,
                data_dir=paths.data_dir,
                output_dir=paths.output_dir,
                manifest=paths.manifest,
                expected_orgao=orgao,
                equipe_path=equipe_path,
                periodo=periodo,
                strict=request.strict,
                collect=collect,
            )
        )
        per_orgao[orgao] = collect
    if request.orgao == 'both':
        # Single markdown per indicator covering both orgãos, alongside the
        # per-orgão ROMs (roms/MinC/..., roms/MTur/...).
        write_combined_roms(
            per_orgao, request.competencia, request.output_dir, periodo=periodo
        )
    return exit_code_for_results(measure_results)


def _dispatch_split(args: argparse.Namespace) -> int:
    from pyauditor.cli.results import validate_competencia

    request = extract_split_request(args)
    if (msg := validate_competencia(request.competencia)) is not None:
        print(msg, file=sys.stderr)
        return 2
    # Log fica junto dos artefatos _split (issue 11), não em
    # data_dir/<orgao>/<competencia>
    # e sem pasta órfã "both"
    year, month = request.competencia.split('-')
    periodo: PeriodoAfericao = month_bounds(request.competencia)
    prazos_path = request.data_dir / PRAZOS_FILENAME
    capa_path = request.data_dir / _CAPA_COMUM
    equipe_path = request.data_dir / EQUIPE_FILENAME
    objetos_path = request.data_dir / _OBJETOS_FILENAME
    split_results = []
    for orgao in _each_single_orgao(request.orgao):
        # setup por órgão dentro do loop para evitar pasta both/ órfã
        setup_logging(
            log_path=_run_log_path(
                request.data_dir / orgao / year / month / '_split',
                _CMD_SPLIT,
                request.competencia,
            ),
            **logging_kwargs(args),
        )
        paths = per_orgao_paths(
            config_dir=request.config_dir,
            data_dir=request.data_dir,
            output_dir=request.data_dir,
            orgao=orgao,
            report_dir=request.report_dir,
        )
        split_results.append(
            run_split(
                competencia=request.competencia,
                config_dir=paths.config_dir,
                data_dir=paths.data_dir,
                expected_orgao=orgao,
                manifest=paths.manifest,
                report_dir=paths.report_dir,
                materialize=True,  # CLI standalone grava os artefatos _split
                periodo=periodo,
                strict=request.strict,
                prazos_path=prazos_path,
                capa_path=capa_path,
                equipe_path=equipe_path,
                objetos_path=objetos_path,
            )
        )
    return exit_code_for_results(split_results)


def _dispatch_bootstrap(args: argparse.Namespace) -> int:
    data_dir = require(args, 'data_dir', Path)
    capa_path = extract_capa_path(args, data_dir=data_dir)
    orgao = require(args, 'orgao', str)
    # bootstrap não tem competencia, nada a validar previamente
    bootstrap_results = []
    for single_orgao in _each_single_orgao(orgao):
        per_orgao_capa = resolve_capa_path(capa_path, cast(Orgao, single_orgao))
        setup_logging(
            log_path=_run_log_path(per_orgao_capa.parent, _CMD_BOOTSTRAP),
            **logging_kwargs(args),
        )
        bootstrap_results.append(run_bootstrap(per_orgao_capa, single_orgao))
    return exit_code_for_results(bootstrap_results)


def _dispatch_report(args: argparse.Namespace) -> int:
    from pyauditor.cli.results import validate_competencia

    report_request = extract_report_request(args)
    if (msg := validate_competencia(report_request.competencia)) is not None:
        print(msg, file=sys.stderr)
        return 2
    setup_logging(
        log_path=_run_log_path(
            report_request.output_path.parent,
            _CMD_REPORT,
            report_request.competencia,
        ),
        **logging_kwargs(args),
    )
    report_results = []
    for orgao in _each_single_orgao(report_request.orgao):
        output_path = (
            report_request.output_path.parent
            / f'relatorio_{report_request.competencia}_{orgao}.xlsx'
        )
        paths = per_orgao_paths(
            config_dir=report_request.config_dir,
            data_dir=report_request.data_dir,
            output_dir=report_request.roms_dir,
            orgao=orgao,
        )
        # `run_report` checa `check_report_ready` internamente (defense-in-depth
        # única, ticket 12) — sem pre-flight duplicado aqui.
        report_results.append(
            run_report(
                competencia=report_request.competencia,
                capa_path=report_request.capa_path,
                roms_dir=paths.output_dir,
                output_path=output_path,
                config_dir=paths.config_dir,
                expected_orgao=orgao,
                is_final_month=report_request.is_final_month,
                data_dir=report_request.data_dir,
            )
        )
    return exit_code_for_results(report_results)


def _dispatch_consolidate(args: argparse.Namespace) -> int:
    from pyauditor.cli.results import validate_competencia

    consolidate_request = extract_consolidate_request(args)
    if (
        msg := validate_competencia(consolidate_request.competencia)
    ) is not None:
        print(msg, file=sys.stderr)
        return 2
    setup_logging(
        log_path=_run_log_path(
            consolidate_request.output_path.parent,
            _CMD_CONSOLIDATE,
            consolidate_request.competencia,
        ),
        **logging_kwargs(args),
    )
    # `run_consolidate` checa `check_consolidate_ready` internamente
    # (defense-in-depth única, ticket 12) — sem pre-flight duplicado aqui.
    consolidate_result = run_consolidate(
        competencia=consolidate_request.competencia,
        report_dir=consolidate_request.report_dir,
        roms_dir=consolidate_request.roms_dir,
        output_path=consolidate_request.output_path,
        data_dir=consolidate_request.data_dir,
        is_final_month=consolidate_request.is_final_month,
    )
    return exit_code_for_results((consolidate_result,))


def _dispatch_run(args: argparse.Namespace) -> int:
    from pyauditor.cli.results import validate_competencia

    competencia = require(args, 'competencia', str)
    if (msg := validate_competencia(competencia)) is not None:
        print(msg, file=sys.stderr)
        return 2
    orgao = require(args, 'orgao', str)
    output_dir = require(args, 'output_dir', Path)
    report_dir = require(args, 'report_dir', Path)
    setup_logging(
        log_path=_run_log_path(report_dir, _CMD_RUN, competencia),
        **logging_kwargs(args),
    )
    output_raw = require(args, 'output', str)
    return run_run(
        competencia=competencia,
        orgao=orgao,
        config_dir=require(args, 'config_dir', Path),
        data_dir=require(args, 'data_dir', Path),
        output_dir=output_dir,
        report_dir=report_dir,
        capa_path=extract_capa_path(
            args, data_dir=require(args, 'data_dir', Path)
        ),
        final_month=bool(cast(object, getattr(args, 'final_month', False))),
        output='json' if output_raw == 'json' else 'text',
        force=bool(cast(object, getattr(args, 'force', False))),
        strict=bool(cast(object, getattr(args, 'strict', False))),
    )


def cli_main(argv: Sequence[str] | None = None) -> int:
    """Dispatch CLI. Returns exit code; never leaks Any."""
    effective_argv = list(argv) if argv is not None else sys.argv[1:]

    if not effective_argv:
        # No args at all -> guided flow (map.md decision). A named command with
        # missing required args still falls through to argparse's normal error.
        if not sys.stdin.isatty():
            print(
                'nenhum terminal detectado — use um subcomando diretamente, '
                'ex.: `pyauditor measure 2026-06`',
                file=sys.stderr,
            )
            return 2
        from pyauditor.interactive import (
            run_interactive,
        )  # local: TTY-gated import

        return run_interactive()

    parser = build_parser()
    args = parser.parse_args(effective_argv)

    # Boundary: Namespace.command is Any -> object -> str
    command_raw: object = cast(object, getattr(args, 'command', None))
    if not isinstance(command_raw, str):
        parser.error('comando ausente')

    if not _is_command(command_raw):
        parser.error(f'comando desconhecido: {command_raw}')

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


def main() -> NoReturn:
    sys.exit(cli_main())


if __name__ == '__main__':
    main()
