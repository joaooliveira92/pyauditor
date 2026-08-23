"""`pyauditor inms-grouped <competência>` — grava
`planilha_inms_agrupada_<competência>.xlsx`: uma visão do `INMS_BASE`
consolidado com agrupamento nativo de linhas do Excel (3 níveis: Código
INMS -> subtotal por órgão -> detalhe por grupo executor), pedida pelo
fiscal para auditar rapidamente sem perder o detalhe original.

Nunca re-roda `consolidate`: requer que
`reports/relatorio_<comp>_consolidado.xlsx` já exista (mesmo contrato de
precondição de `consolidate` em relação a `report`) — erro nomeando o
arquivo ausente em vez de gerá-lo.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from pyauditor.atomic_write import atomic_write
from pyauditor.cli.results import (
    WRITE_FAILURE_HINT,
    DependencyCheck,
    validate_competencia,
)
from pyauditor.commands import contracts
from pyauditor.excel.inms_grouped import build_inms_grouped_workbook
from pyauditor.logging import log_event, logger

InmsGroupedResult = contracts.InmsGroupedResult


def check_inms_grouped_ready(
    competencia: str, report_dir: Path
) -> DependencyCheck:
    """`inms-grouped` precisa do consolidado do `consolidate` já publicado."""
    consolidado_path = report_dir / f'relatorio_{competencia}_consolidado.xlsx'
    missing = () if consolidado_path.is_file() else (str(consolidado_path),)
    return DependencyCheck(satisfied=not missing, missing=missing)


def run_inms_grouped(
    competencia: str,
    report_dir: Path,
    config_dir: Path,
    data_dir: Path,
    output_path: Path,
) -> InmsGroupedResult:
    def _error(message: str) -> InmsGroupedResult:
        logger.error(message)
        return InmsGroupedResult(
            status='error',
            competencia=competencia,
            output_path=output_path,
            code_groups=0,
            org_subgroups=0,
            total_rows=0,
            breakdown_codes=(),
            error_message=message,
        )

    competencia_error = validate_competencia(competencia)
    if competencia_error is not None:
        return _error(competencia_error)

    dependency_check = check_inms_grouped_ready(competencia, report_dir)
    if not dependency_check.satisfied:
        return _error(
            'dependência não satisfeita: ' + '; '.join(dependency_check.missing)
        )

    consolidado_path = report_dir / f'relatorio_{competencia}_consolidado.xlsx'

    try:
        # `build_inms_grouped_workbook` só precisa de `scratch_dir` porque
        # `resolve_measure_inputs` exige um `target_dir` gravável — nada é
        # persistido ali (é leitura de configs/CSV), então um diretório
        # temporário descartável evita acumular lixo em `reports/`.
        with tempfile.TemporaryDirectory(
            prefix='pyauditor-inms-grouped-'
        ) as scratch:
            result = build_inms_grouped_workbook(
                competencia,
                consolidado_path,
                config_dir,
                data_dir,
                scratch_dir=Path(scratch),
            )
    except (FileNotFoundError, ValueError) as exc:
        return _error(str(exc))
    except Exception as exc:  # boundary: never leak a raw traceback
        return _error(
            f'falha inesperada ao montar planilha agrupada de {competencia}: '
            f'{exc}'
        )

    try:
        atomic_write(output_path, result.workbook.save)
    except OSError as exc:
        return _error(
            f'falha ao escrever {output_path}: {exc} — {WRITE_FAILURE_HINT}'
        )
    finally:
        result.workbook.close()

    log_event(
        'inms_grouped_generated',
        'planilha agrupada gerada',
        'INFO',
        arquivo=str(output_path),
        codigos_inms=str(result.code_groups),
        subgrupos=str(result.org_subgroups),
        detalhamento=','.join(result.breakdown_codes) or '-',
    )
    return InmsGroupedResult(
        status='done',
        competencia=competencia,
        output_path=output_path,
        code_groups=result.code_groups,
        org_subgroups=result.org_subgroups,
        total_rows=result.total_rows,
        breakdown_codes=result.breakdown_codes,
        error_message=None,
    )
