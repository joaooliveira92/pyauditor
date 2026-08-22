"""Schema do parser CLI (`argparse`) — sem orquestração (ticket 01 SRP).

Extraído de `cli/main.py`: só registra argumentos e sub-comandos. A tradução
argparse→request fica em `cli/requests.py`; o dispatch multi-órgão, em
`cli/main.py`.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Final, Literal

__all__: Final[tuple[str, ...]] = (
    'Command',
    'Orgao',
    'build_parser',
)

_PROG: Final[str] = 'pyauditor'
_CMD_MEASURE: Final = 'measure'
_CMD_BOOTSTRAP: Final = 'bootstrap'
_CMD_REPORT: Final = 'report'
_CMD_CONSOLIDATE: Final = 'consolidate'
_CMD_SPLIT: Final = 'split'
_CMD_RUN: Final = 'run'

type Command = Literal[
    'measure', 'bootstrap', 'report', 'consolidate', 'split', 'run'
]

type Orgao = Literal['MinC', 'MTur', 'both']

_DEFAULT_CONFIG_DIR: Final[Path] = Path('configs')
_DEFAULT_DATA_DIR: Final[Path] = Path('input')
_DEFAULT_OUTPUT_DIR: Final[Path] = Path('roms')
_DEFAULT_CAPA_PATH: Final[Path] = Path('capa.xlsx')
_DEFAULT_REPORT_DIR: Final[Path] = Path('reports')

_STRICT_HELP = (
    'descarta linhas sem prova de período (célula vazia ou formato '
    'desconhecido) em vez de mantê-las para os quality gates'
)


def _add_orgao_argument(
    parser: argparse.ArgumentParser, *, default: Orgao = 'MinC'
) -> None:
    parser.add_argument(
        '--orgao',
        type=str,
        choices=('MinC', 'MTur', 'both'),
        default=default,
        help='órgão '
        'da '
        'aferição '
        '(default: '
        'MinC). '
        "'both' "
        'roda '
        'os '
        'dois, '
        'sequencial, '
        'sem '
        'cruzar',
    )


def _add_strict_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument('--strict', action='store_true', help=_STRICT_HELP)


def _add_logging_arguments(parser: argparse.ArgumentParser) -> None:
    """Flags de observabilidade (ticket 05): verbosidade `-v`/`-vv`, nível
    explícito e formato JSON para automação. Aplicado a todos os subcomandos
    (Q8): o nível efetivo = `--log-level` se dado, senão a verbosidade."""
    parser.add_argument(
        '-v',
        '--verbose',
        action='count',
        default=0,
        help='-v:umeventoporindicador;-vv:detalhesdeleitura/validação/cálculo',
    )
    parser.add_argument(
        '--log-level',
        type=str,
        choices=('DEBUG', 'INFO', 'WARNING', 'ERROR'),
        default=None,
        help='nível de log manual (prevalece sobre -v; default INFO)',
    )
    parser.add_argument(
        '--log-format',
        type=str,
        choices=('text', 'json'),
        default='text',
        help='json: '
        'cada '
        'registro '
        'em '
        'stderr '
        'vira '
        'uma '
        'linha '
        'JSON '
        '({time, level, event, ...})',
    )


def build_parser() -> argparse.ArgumentParser:
    """Arg parser estruturado e estrito (spec §6), sem efeito colateral."""
    parser = argparse.ArgumentParser(prog=_PROG)
    subparsers = parser.add_subparsers(dest='command', required=True)

    measure_parser = subparsers.add_parser(
        _CMD_MEASURE,
        help='apura os indicadores de uma competência',
    )
    measure_parser.add_argument('competencia', help='ex.: "2026-06"')
    _add_orgao_argument(measure_parser)
    measure_parser.add_argument(
        '--config-dir', type=Path, default=_DEFAULT_CONFIG_DIR
    )
    measure_parser.add_argument(
        '--data-dir', type=Path, default=_DEFAULT_DATA_DIR
    )
    measure_parser.add_argument(
        '--output-dir', type=Path, default=_DEFAULT_OUTPUT_DIR
    )
    measure_parser.add_argument(
        '--manifest',
        type=Path,
        default=None,
        help='caminho para datasets.yaml (default: resolvido a partir de '
        '--config-dir — _shared se existir, senão <config-dir>/<órgão>)',
    )
    _add_strict_argument(measure_parser)
    _add_logging_arguments(measure_parser)

    bootstrap_parser = subparsers.add_parser(
        _CMD_BOOTSTRAP,
        help='criaascapasCSVdocontrato(comum+porórgão),seaindanãoexistirem',
    )
    _add_orgao_argument(bootstrap_parser)
    bootstrap_parser.add_argument(
        '--data-dir',
        type=Path,
        default=_DEFAULT_DATA_DIR,
        help=f'onde criar capa.csv e capa_{{orgao}}.csv (default: {_DEFAULT_DATA_DIR})',
    )
    bootstrap_parser.add_argument(
        '--capa-path',
        type=Path,
        default=None,
        help='caminho do capa comum (cap.csv); default: <data-dir>/capa.csv',
    )
    _add_logging_arguments(bootstrap_parser)

    report_parser = subparsers.add_parser(
        _CMD_REPORT, help='consolida os ROMs de uma competência no Excel final'
    )
    report_parser.add_argument('competencia', help='ex.: "2026-06"')
    _add_orgao_argument(report_parser)
    report_parser.add_argument(
        '--data-dir',
        type=Path,
        default=_DEFAULT_DATA_DIR,
        help='onde vivem capa_{orgao}.csv e objetos.csv (default: input)',
    )
    report_parser.add_argument(
        '--capa-path',
        type=Path,
        default=None,
        help='caminho do capa comum capa.csv (default: <data-dir>/capa.csv)',
    )
    report_parser.add_argument(
        '--roms-dir', type=Path, default=_DEFAULT_OUTPUT_DIR
    )
    report_parser.add_argument(
        '--output-dir', type=Path, default=_DEFAULT_REPORT_DIR
    )
    report_parser.add_argument(
        '--config-dir', type=Path, default=_DEFAULT_CONFIG_DIR
    )
    report_parser.add_argument(
        '--final-month',
        action='store_true',
        help='último '
        'mês '
        'de '
        'vigência '
        'do '
        'contrato '
        '— '
        'desliga '
        'o '
        'rollover '
        'de '
        'glosa '
        '(item '
        '35 '
        'do '
        'TR)',
    )
    _add_logging_arguments(report_parser)

    consolidate_parser = subparsers.add_parser(
        _CMD_CONSOLIDATE,
        help='funde '
        'os '
        'relatórios '
        'MinC+MTur '
        'já '
        'gerados '
        'na '
        'planilha '
        'financeira '
        'consolidada',
    )
    consolidate_parser.add_argument('competencia', help='ex.: "2026-06"')
    consolidate_parser.add_argument(
        '--report-dir', type=Path, default=_DEFAULT_REPORT_DIR
    )
    consolidate_parser.add_argument(
        '--roms-dir', type=Path, default=_DEFAULT_OUTPUT_DIR
    )
    consolidate_parser.add_argument(
        '--data-dir',
        type=Path,
        default=_DEFAULT_DATA_DIR,
        help='onde vive objetos.csv, a fonte do valor mensal (default: input)',
    )
    consolidate_parser.add_argument(
        '--final-month',
        action='store_true',
        help='último '
        'mês '
        'de '
        'vigência '
        'do '
        'contrato '
        '— '
        'desliga '
        'o '
        'rollover '
        'de '
        'glosa '
        '(item '
        '35 '
        'do '
        'TR)',
    )
    _add_logging_arguments(consolidate_parser)

    split_parser = subparsers.add_parser(
        _CMD_SPLIT,
        help='geraCSVsfiltrados+configsderivadasporCategoria(spec§14.3)',
    )
    split_parser.add_argument('competencia', help='ex.: "2026-06"')
    _add_orgao_argument(split_parser)
    split_parser.add_argument(
        '--config-dir', type=Path, default=_DEFAULT_CONFIG_DIR
    )
    split_parser.add_argument(
        '--data-dir', type=Path, default=_DEFAULT_DATA_DIR
    )
    split_parser.add_argument(
        '--report-dir', type=Path, default=_DEFAULT_REPORT_DIR
    )
    split_parser.add_argument(
        '--manifest',
        type=Path,
        default=None,
        help='caminho para datasets.yaml (default: resolvido a partir de '
        '--config-dir — _shared se existir, senão <config-dir>/<órgão>)',
    )
    _add_strict_argument(split_parser)
    _add_logging_arguments(split_parser)

    run_parser = subparsers.add_parser(
        _CMD_RUN,
        help='encadeia '
        'bootstrap→measure→report→consolidate '
        'numa '
        'invocação '
        'scriptável',
    )
    run_parser.add_argument('competencia', help='ex.: "2026-06"')
    _add_orgao_argument(run_parser)
    run_parser.add_argument(
        '--config-dir', type=Path, default=_DEFAULT_CONFIG_DIR
    )
    run_parser.add_argument('--data-dir', type=Path, default=_DEFAULT_DATA_DIR)
    run_parser.add_argument(
        '--output-dir', type=Path, default=_DEFAULT_OUTPUT_DIR
    )
    run_parser.add_argument(
        '--report-dir', type=Path, default=_DEFAULT_REPORT_DIR
    )
    run_parser.add_argument('--capa-path', type=Path, default=None)
    _add_strict_argument(run_parser)
    run_parser.add_argument(
        '--output',
        type=str,
        choices=('text', 'json'),
        default='text',
        help='formato '
        'do '
        'resumo '
        'final: '
        "'text' "
        '(painel '
        'rico, '
        'padrão) '
        'ou '
        "'json' "
        '(automação/CI)',
    )
    _add_logging_arguments(run_parser)
    run_parser.add_argument(
        '--final-month',
        action='store_true',
        help='último '
        'mês '
        'de '
        'vigência '
        'do '
        'contrato '
        '— '
        'desliga '
        'o '
        'rollover '
        'de '
        'glosa '
        '(item '
        '35 '
        'do '
        'TR)',
    )
    run_parser.add_argument(
        '--force',
        action='store_true',
        help=(
            'reprocessa tudo, mesmo etapas já concluídas numa tentativa '
            'anterior '
            "(default: retoma de onde parou, pulando o que já está 'done')"
        ),
    )

    return parser
