"""Render the shared completion summary for an orchestration run.

This module is the canonical completion-summary renderer used by both the
non-interactive ``run`` command and the interactive provider. It performs no
prompting and writes only to the supplied Rich console.

Two output formats are supported:

``text``
    Human-readable command table, result panel, artifact paths, log path, and
    actionable next steps.

``json``
    A single plain JSON document intended for automation. The JSON model is
    `summary_json` (máquina); alive querying of the schema lives in
    `orchestration/summary_json.py` (ticket 06 SRP).

The renderer is deliberately defensive. Unknown commands, missing results, and
partially completed runs remain visible in the summary instead of causing the
summary itself to fail. Dynamic paths, organization names, and error messages
are rendered as literal text and are never interpreted as Rich markup.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from decimal import Decimal
from math import isfinite
from pathlib import Path
from typing import Final, Literal

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from pyauditor.cli.bootstrap import BootstrapResult
from pyauditor.cli.consolidate import ConsolidateResult
from pyauditor.cli.measure import MeasureResult
from pyauditor.cli.report import ReportResult
from pyauditor.cli.results import exit_code_name, is_production_command
from pyauditor.cli.split import SplitResult
from pyauditor.orchestration.run import (
    RunResult,
    dependency_missing,
)
from pyauditor.orchestration.state import (
    CommandStateEntry,
)
from pyauditor.orchestration.summary_json import (
    _artifact_paths,
    _consolidated_info,
    _duration_ms,
    _errors_count,
    _organization_summary,
    _orgaos_no_run,
    _result_for,
    _warnings_count,
    summary_json,
)
from pyauditor.state_presentation import (
    STATE_PRESENTATION,
    UNKNOWN_STATE_PRESENTATION,
)

__all__: Final[tuple[str, ...]] = (
    'OutputFormat',
    'exit_code_for_run',
    'fmt_pt_br',
    'render_summary',
    'summary_json',
)

type OutputFormat = Literal['text', 'json']
type CommandResult = (
    BootstrapResult
    | SplitResult
    | MeasureResult
    | ReportResult
    | ConsolidateResult
)

_VALID_OUTPUT_FORMATS: Final[frozenset[str]] = frozenset(
    {
        'text',
        'json',
    }
)


def exit_code_for_run(
    state_commands: Sequence[CommandStateEntry],
    results: Sequence[object],
) -> int:
    """Calculate the aggregate process exit code.

    Exit-code precedence is ``1 > 4 > 3 > 0``:

    - ``1`` indicates that at least one command ended in technical error;
    - ``4`` indicates that a report or consolidation result could not
      calculate the financial adjustment;
    - ``3`` indicates that a production command was skipped or that a
      generated result is not publishable;
    - ``0`` indicates successful production without publication blockers.
    """
    if any(entry.status == 'error' for entry in state_commands):
        return 1

    if any(
        getattr(result, 'glosa_calculada', True) is False for result in results
    ):
        return 4

    if any(
        entry.status == 'skipped' and is_production_command(entry.command)
        for entry in state_commands
    ):
        return 3

    if any(getattr(result, 'publicable', True) is False for result in results):
        return 3

    return 0


def _bootstrap_artifact(result: BootstrapResult) -> str:
    """Describe the artifact produced by bootstrap."""
    return str(result.capa_path)


def _split_artifact(result: SplitResult) -> str:
    """Describe split output and non-fatal warnings."""
    parts = [
        f'{len(result.categorias)} categoria(s) processada(s)',
    ]

    if result.sintetico_path is not None:
        parts.append(str(result.sintetico_path))

    if result.warnings:
        parts.append(f'{len(result.warnings)} aviso(s)')

    return ' | '.join(parts)


def _measure_artifact(result: MeasureResult) -> str:
    """Describe measured indicators and hard failures."""
    failing = [
        indicator.contractual_id
        for indicator in result.indicators
        if indicator.hard_failure
    ]

    description = f'{len(result.indicators)} indicador(es) apurado(s)'

    if failing:
        description += f' | falhas: {", ".join(failing)}'

    return description


def _report_artifact(result: ReportResult) -> str:
    """Describe an individual report artifact."""
    return f'{result.output_path} ({result.indicator_count} indicadores)'


def _consolidate_artifact(
    result: ConsolidateResult,
) -> str:
    """Describe the consolidated report artifact."""
    return (
        f'{result.output_path}'
        f'({result.decisions_preserved}'
        f'decisão(ões)'
        f'preservada(s))'
    )


def _artifact_line(
    entry: CommandStateEntry,
    result: CommandResult | None,
) -> str:
    """Return the literal artifact description for a command row."""
    if result is None:
        if entry.status == 'skipped':
            return 'pulado'

        if entry.status == 'done':
            return 'resultado indisponível ou ambíguo'

        return '-'

    if isinstance(result, BootstrapResult):
        return _bootstrap_artifact(result)

    if isinstance(result, SplitResult):
        return _split_artifact(result)

    if isinstance(result, MeasureResult):
        return _measure_artifact(result)

    if isinstance(result, ReportResult):
        return _report_artifact(result)

    if isinstance(result, ConsolidateResult):
        return _consolidate_artifact(result)

    return '-'


def fmt_pt_br(
    value: float | Decimal,
    *,
    decimals: int = 2,
) -> str:
    """Format a finite number using Brazilian separators.

    The returned representation uses ``.`` as the thousands separator and
    ``,`` as the decimal separator. This helper is intended only for
    human-readable output. JSON output retains machine-oriented numeric
    representations.
    """
    if isinstance(decimals, bool) or not isinstance(decimals, int):
        raise TypeError('decimals must be an integer')

    if decimals < 0:
        raise ValueError('decimals must not be negative')

    if isinstance(value, bool):
        raise TypeError('value must not be boolean')

    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError('value must be finite')
        raw = f'{value:.{decimals}f}'
    elif isinstance(value, float):
        if not isfinite(value):
            raise ValueError('value must be finite')
        raw = f'{value:.{decimals}f}'
    else:
        raise TypeError(
            f'value must be float or Decimal, received {type(value).__name__}'
        )

    integer_part, separator, fractional_part = raw.partition('.')
    sign = ''

    if integer_part.startswith('-'):
        sign = '-'
        integer_part = integer_part[1:]

    grouped_integer = f'{int(integer_part):,}'.replace(',', '.')
    localized_integer = f'{sign}{grouped_integer}'

    if not separator or decimals == 0:
        return localized_integer

    return f'{localized_integer},{fractional_part}'


def _next_steps(run_result: RunResult) -> list[str]:
    """Return deduplicated actionable recovery instructions."""
    steps: list[str] = []
    incomplete_organizations: set[str] = set()

    for entry in run_result.state.commands:
        if entry.status == 'done':
            continue

        missing = dependency_missing(
            entry.command,
            entry.orgao,
            run_result.request,
        )

        if missing:
            organization = entry.orgao or '-'
            steps.append(
                f'{entry.command} ({organization}): {", ".join(missing)}'
            )

        if entry.orgao is not None and entry.status in {'error', 'skipped'}:
            incomplete_organizations.add(entry.orgao)

    for organization in _orgaos_no_run(run_result):
        if organization not in incomplete_organizations:
            continue

        steps.append(
            f'{organization}: relatório não gerado; execute '
            f'`pyauditor run {run_result.competencia} '
            f'--orgao {organization}` para completar somente esse órgão'
        )

    return list(dict.fromkeys(steps))


def _result_panel(
    run_result: RunResult,
    exit_code: int,
) -> Panel:
    """Build the global human-readable result panel."""
    organizations = {
        organization: _organization_summary(
            run_result,
            organization,
        )
        for organization in _orgaos_no_run(run_result)
    }

    indicator_counts = ', '.join(
        (
            f'{organization} '
            f'{summary["indicadores"]["aferidos"]}/'
            f'{summary["indicadores"]["total_esperado"]}'
        )
        for organization, summary in organizations.items()
    )
    if not indicator_counts:
        indicator_counts = '-'

    generated_reports = sum(
        1 for summary in organizations.values() if summary['relatorio_gerado']
    )
    drafts = [
        organization
        for organization, summary in organizations.items()
        if summary['relatorio_gerado'] and not summary['publicable']
    ]

    report_description = f'{generated_reports}/{len(organizations)} gerado(s)'
    if drafts:
        report_description += (
            f' | {len(drafts)} rascunho(s): {", ".join(drafts)}'
        )

    glosa_states = {summary['glosa'] for summary in organizations.values()}
    if not glosa_states:
        glosa_description = 'não disponível'
    elif 'não calculada' in glosa_states:
        glosa_description = 'não calculada'
    else:
        glosa_description = 'calculada'

    if exit_code == 0:
        publication = 'liberada'
    elif exit_code == 4:
        publication = 'bloqueada: cálculo financeiro indisponível'
    elif exit_code == 3:
        reason = next(
            (
                summary['motivo_publicacao']
                for summary in organizations.values()
                if summary['motivo_publicacao'] is not None
            ),
            None,
        )
        publication = (
            f'bloqueada: {reason}'
            if reason is not None
            else 'bloqueada: etapa final não gerada'
        )
    else:
        publication = 'não informada devido a falha técnica'

    consolidated = _consolidated_info(run_result)
    duration_ms = _duration_ms(run_result)

    if duration_ms is None:
        duration_description = 'indisponível'
    else:
        duration_description = f'{fmt_pt_br(duration_ms / 1000.0)} s'

    total_points: str
    if consolidated is None:
        total_points = '-'
    else:
        raw_points = consolidated['total_pontos']
        if isinstance(raw_points, str):
            total_points = fmt_pt_br(Decimal(raw_points))
        elif isinstance(raw_points, int):
            total_points = fmt_pt_br(float(raw_points))
        else:
            total_points = fmt_pt_br(raw_points)

    content = Text()
    content.append('Resultado: ', style='bold')
    content.append(exit_code_name(exit_code))
    content.append('\nCompetência: ', style='bold')
    content.append(run_result.competencia)
    content.append('\nÓrgãos no plano: ', style='bold')
    content.append(str(len(organizations)))
    content.append('\nIndicadores apurados: ', style='bold')
    content.append(indicator_counts)
    content.append('\nRelatórios individuais: ', style='bold')
    content.append(report_description)
    content.append('\nRelatório consolidado: ', style='bold')
    content.append('gerado' if consolidated is not None else 'não gerado')
    content.append(
        '\nTotal de pontos do consolidado: ',
        style='bold',
    )
    content.append(total_points)
    content.append('\nAvisos: ', style='bold')
    content.append(str(_warnings_count(run_result)))
    content.append('\nErros: ', style='bold')
    content.append(str(_errors_count(run_result)))
    content.append('\nGlosa monetária: ', style='bold')
    content.append(glosa_description)
    content.append('\nPublicação: ', style='bold')
    content.append(publication)
    content.append('\nDuração: ', style='bold')
    content.append(duration_description)

    return Panel(
        content,
        title='Resultado',
        border_style='white',
    )


def _command_table(run_result: RunResult) -> Table:
    """Build the human-readable command-state table."""
    table = Table(
        box=None,
        show_header=True,
        header_style='bold',
    )
    table.add_column('')
    table.add_column('Comando')
    table.add_column('Órgão')
    table.add_column('Artefatos / avisos')

    for entry in run_result.state.commands:
        icon, style = STATE_PRESENTATION.get(
            entry.status,
            UNKNOWN_STATE_PRESENTATION,
        )
        result = _result_for(
            command=entry.command,
            orgao=entry.orgao,
            results=run_result.results,
        )

        detail = Text(entry.error_message or _artifact_line(entry, result))

        if isinstance(result, ReportResult) and not result.publicable:
            detail.append(
                ' (rascunho, não publicável)',
                style='dim',
            )

        table.add_row(
            Text(icon, style=style),
            Text(entry.command),
            Text(entry.orgao or '-'),
            detail,
        )

    return table


def _lines_panel(
    lines: Sequence[str],
    *,
    title: str,
    border_style: str,
) -> Panel:
    """Build a panel whose dynamic lines are rendered literally."""
    content = Text()

    for index, line in enumerate(lines):
        if index:
            content.append('\n')
        content.append(line)

    return Panel(
        content,
        title=title,
        border_style=border_style,
    )


def render_summary(
    run_result: RunResult,
    *,
    log_path: Path | str | None = None,
    output: OutputFormat = 'text',
    console: Console | None = None,
) -> None:
    """Render the final summary for an orchestration run.

    ``text`` output contains the command table, global result panel, complete
    artifact paths, optional log path, and actionable recovery instructions.

    ``json`` output contains exactly one plain JSON document.

    Args:
        run_result: Completed orchestration result.
        log_path: Optional path to the complete technical log.
        output: Output format, either ``text`` or ``json``.
        console: Destination console. A standard Rich console is created when
            omitted.

    Raises:
        ValueError: If ``output`` is unsupported or structured numeric values
            are non-finite.
        TypeError: If structured numeric values have unsupported types.
    """
    if output not in _VALID_OUTPUT_FORMATS:
        raise ValueError(f'Unsupported summary output format: {output!r}.')

    destination = console if console is not None else Console()
    exit_code = exit_code_for_run(
        run_result.state.commands,
        run_result.results,
    )

    if output == 'json':
        payload = json.dumps(
            summary_json(run_result, exit_code),
            ensure_ascii=False,
            separators=(',', ':'),
            allow_nan=False,
        )
        destination.print(
            payload,
            markup=False,
            highlight=False,
            soft_wrap=True,
        )
        return

    destination.print(_command_table(run_result))
    destination.print(_result_panel(run_result, exit_code))

    artifact_paths = _artifact_paths(run_result)
    if artifact_paths:
        destination.print(
            _lines_panel(
                tuple(f'  * {path}' for path in artifact_paths),
                title='Artefatos',
                border_style='cyan',
            )
        )

    if log_path is not None:
        log_line = Text('Log completo: ', style='dim')
        log_line.append(str(log_path), style='dim')
        destination.print(log_line)

    next_steps = _next_steps(run_result)
    if next_steps:
        destination.print(
            _lines_panel(
                next_steps,
                title='Próximos passos',
                border_style='cyan',
            )
        )
