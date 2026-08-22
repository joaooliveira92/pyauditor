"""Run the provider-independent guided audit flow.

This module defines the interactive screen sequence used to collect a run
request, select commands, execute the shared orchestrator, and display the
completion summary.

All user interaction goes through :class:`InteractionProvider`. The module
does not import or depend directly on Rich, Questionary, or another terminal
UI implementation.

Business sequencing, dependency checks, resume behavior, state persistence,
and failure isolation remain the responsibility of
:func:`pyauditor.orchestration.run.execute_run`. This module only decides
which screen appears next and translates user choices into orchestration
callbacks.

Após o split SRP (ticket 05): o formulário vive em `interactive/fields.py`, o
catálogo/política de comandos em `interactive/commands.py` e a apresentação de
estado em `interactive/status_view.py`. Este módulo orquestra as telas.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from pyauditor.interactive.commands import (
    ALL_COMMANDS,
    COMMAND_LABELS,
    force_commands_for,
)
from pyauditor.interactive.fields import (
    Field,
    fields_spec,
    validate_non_empty_text,
)
from pyauditor.interactive.provider import (
    InteractionCancelledError,
    InteractionProvider,
    RichQuestionaryProvider,
)
from pyauditor.interactive.status_view import render_state_line
from pyauditor.orchestration.run import (
    FailureDecision,
    RunRequest,
    execute_run,
)
from pyauditor.orchestration.state import (
    CommandStateEntry,
)

__all__: Final[tuple[str, ...]] = (
    'GuidedAnswers',
    'collect_answers',
    'run_guided_flow',
    'run_interactive',
    'select_commands',
    'show_opening',
)

_HELP_TOKEN: Final[str] = '?'
_CANCELLED_EXIT_CODE: Final[int] = 130

_PRE_DISPATCH_FAILURE_PREFIX: Final[str] = 'dependência não satisfeita:'


@dataclass(frozen=True, slots=True)
class GuidedAnswers:
    """Contain the validated answers collected by the guided flow.

    Attributes:
        competencia: Reporting period in ``YYYY-MM`` format.
        orgao: Organization selector: ``MinC``, ``MTur``, or ``both``.
        config_dir: Root configuration directory.
        data_dir: Root input-data directory.
        output_dir: Destination root for generated ROMs.
        report_dir: Destination directory for report workbooks.
        capa_path: Base path used to resolve organization cover files.
    """

    competencia: str
    orgao: str
    config_dir: Path
    data_dir: Path
    output_dir: Path
    report_dir: Path
    capa_path: Path


def _ask_with_help(
    provider: InteractionProvider,
    ask: Callable[[], str],
    help_text: str,
) -> str:
    """Ask a free-text or choice question with contextual help.

    The prompt is repeated whenever the provider returns ``?``.
    """
    while True:
        answer = ask()

        if answer == _HELP_TOKEN:
            provider.show_message(
                help_text,
                style='dim',
            )
            continue

        return answer


def _ask_path(
    provider: InteractionProvider,
    prompt: str,
    *,
    default: str,
    help_text: str,
) -> Path:
    """Collect a non-empty filesystem path with contextual help."""
    answer = _ask_with_help(
        provider,
        lambda: provider.ask_text(
            prompt,
            default=default,
            validate=validate_non_empty_text,
        ),
        help_text,
    )

    return Path(answer.strip()).expanduser()


def show_opening(provider: InteractionProvider) -> None:
    """Display the guided-flow introduction."""
    provider.show_message(
        "pyauditor: aferição guiada. Digite '?' nas perguntas de texto "
        'para obter ajuda contextual. Ctrl+C encerra o fluxo; etapas de '
        'processamento já registradas poderão ser retomadas.',
        style='bold cyan',
    )


def _collect_field(provider: InteractionProvider, field: Field) -> str | Path:
    """Collect one declarative field through the provider."""
    if field.key == 'orgao':
        orgao_choice = _ask_with_help(
            provider,
            lambda: provider.ask_choice(
                field.prompt,
                (
                    'MinC',
                    'MTur',
                    'both: MinC e MTur',
                ),
                default=field.default,
            ),
            field.help_text,
        )
        return 'both' if orgao_choice.startswith('both') else orgao_choice

    if field.is_path:
        return _ask_path(
            provider,
            field.prompt,
            default=field.default,
            help_text=field.help_text,
        )

    validator = field.validate or validate_non_empty_text
    answer = _ask_with_help(
        provider,
        lambda: provider.ask_text(
            field.prompt,
            validate=validator,
        ),
        field.help_text,
    )
    return answer


def collect_answers(
    provider: InteractionProvider,
) -> GuidedAnswers:
    """Collect and confirm the inputs required by the orchestrator.

    Declining confirmation restarts collection with a loop rather than
    recursion, allowing any number of revisions without increasing the call
    stack.
    """
    while True:
        values = {
            field.key: _collect_field(provider, field) for field in fields_spec
        }

        answers = GuidedAnswers(
            competencia=str(values['competencia']),
            orgao=str(values['orgao']),
            config_dir=Path(values['config_dir']),
            data_dir=Path(values['data_dir']),
            output_dir=Path(values['output_dir']),
            report_dir=Path(values['report_dir']),
            capa_path=Path(values['capa_path']),
        )

        if provider.confirm(
            'Os dados informados estão corretos?',
            default=True,
        ):
            return answers

        provider.show_message(
            'Vamos revisar as informações.',
            style='yellow',
        )


def select_commands(
    provider: InteractionProvider,
    orgao: str,
) -> frozenset[str]:
    """Collect a non-empty set of commands for the selected plan.

    Consolidation is available only for ``both``. The provider may allow the
    user to omit upstream commands when their artifacts already exist; the
    orchestrator remains responsible for checking those dependencies.
    """
    if orgao not in {'MinC', 'MTur', 'both'}:
        raise ValueError(f'Seletor de órgão não suportado: {orgao!r}.')

    consolidate_available = orgao == 'both'
    choices: list[tuple[str, str, bool, str | None]] = []

    for command in ALL_COMMANDS:
        if command == 'consolidate':
            choices.append(
                (
                    COMMAND_LABELS[command],
                    command,
                    consolidate_available,
                    (
                        None
                        if consolidate_available
                        else 'disponível somente para both'
                    ),
                )
            )
            continue

        choices.append(
            (
                COMMAND_LABELS[command],
                command,
                True,
                None,
            )
        )

    while True:
        selected = provider.ask_multi_choice(
            'Selecione as etapas:',
            choices,
        )

        if selected:
            return frozenset(selected)

        provider.show_message(
            'Selecione ao menos uma etapa para iniciar a execução.',
            style='yellow',
        )


def _is_pre_dispatch_failure(
    entry: CommandStateEntry,
) -> bool:
    """Return whether an error was produced by a dependency check.

    The persisted state contract requires timestamps for every ``error``
    transition, including pre-dispatch failures. Until failure stage becomes
    an explicit state field, the orchestrator's controlled dependency-message
    prefix is the canonical discriminator.
    """
    message = entry.error_message or ''
    return message.startswith(_PRE_DISPATCH_FAILURE_PREFIX)


def run_guided_flow(
    provider: InteractionProvider,
) -> int:
    """Run the complete guided flow and translate cancellation to exit 130."""
    try:
        return _run_guided_flow(provider)
    except InteractionCancelledError:
        provider.show_message(
            'Execução encerrada pelo usuário. Etapas de processamento já '
            'registradas foram preservadas e poderão ser retomadas.',
            style='yellow',
        )
        return _CANCELLED_EXIT_CODE


def _run_guided_flow(
    provider: InteractionProvider,
) -> int:
    """Collect inputs, execute the orchestrator, and show its summary."""
    show_opening(provider)
    answers = collect_answers(provider)
    commands = select_commands(
        provider,
        answers.orgao,
    )

    request = RunRequest(
        competencia=answers.competencia,
        orgao=answers.orgao,
        config_dir=answers.config_dir,
        data_dir=answers.data_dir,
        output_dir=answers.output_dir,
        report_dir=answers.report_dir,
        capa_path=answers.capa_path,
        commands=commands,
        force_commands=force_commands_for(
            answers.orgao,
            commands,
        ),
    )

    def on_state_change(
        entry: CommandStateEntry,
    ) -> None:
        """Display one persisted orchestration transition."""
        message, style = render_state_line(entry)
        provider.show_message(
            message,
            style=style,
        )

    def on_failure(
        entry: CommandStateEntry,
    ) -> FailureDecision:
        """Ask how the orchestrator should handle a command failure."""
        reason = entry.error_message or 'falha sem mensagem disponível'
        provider.show_message(
            f'{entry.command} falhou: {reason}',
            style='bold red',
        )

        choices: tuple[str, ...]
        if _is_pre_dispatch_failure(entry):
            choices = (
                'Ignorar esta etapa',
                'Abortar a execução',
            )
        else:
            choices = (
                'Tentar novamente',
                'Ignorar esta etapa',
                'Abortar a execução',
            )

        choice = provider.ask_choice(
            'Como prosseguir?',
            choices,
        )

        if choice.startswith('Tentar'):
            return 'retry'

        if choice.startswith('Ignorar'):
            return 'skip'

        return 'abort'

    run_result = execute_run(
        request,
        on_state_change=on_state_change,
        on_failure=on_failure,
    )
    return provider.show_summary(run_result)


def run_interactive() -> int:
    return run_guided_flow(RichQuestionaryProvider())
