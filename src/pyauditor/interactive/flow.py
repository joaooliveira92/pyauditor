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

The guided flow supports contextual help through ``?`` in every free-text
question. Cancellation is represented by ``InteractionCancelled`` and returns
exit code 130. Only orchestration transitions already persisted before the
cancellation are available for resume.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from pyauditor.interactive.provider import (
    InteractionCancelled,
    InteractionProvider,
)
from pyauditor.orchestration.run import (
    FailureDecision,
    RunRequest,
    execute_run,
)
from pyauditor.orchestration.state import (
    CommandState,
    CommandStateEntry,
)
from pyauditor.periodo import month_bounds

__all__: Final[tuple[str, ...]] = (
    "GuidedAnswers",
    "collect_answers",
    "run_guided_flow",
    "select_commands",
    "show_opening",
)

_HELP_TOKEN: Final[str] = "?"
_CANCELLED_EXIT_CODE: Final[int] = 130

_ALL_COMMANDS: Final[tuple[str, ...]] = (
    "bootstrap",
    "split",
    "measure",
    "report",
    "consolidate",
)

_PRE_DISPATCH_FAILURE_PREFIX: Final[str] = "dependência não satisfeita:"

_STATE_PRESENTATION: Final[dict[CommandState, tuple[str, str]]] = {
    "pending": ("[ ]", "dim"),
    "running": ("[>]", "cyan"),
    "done": ("[x]", "green"),
    "skipped": ("[~]", "yellow"),
    "error": ("[!]", "bold red"),
}

_UNKNOWN_STATE_PRESENTATION: Final[tuple[str, str]] = (
    "[?]",
    "bold red",
)


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


def _validate_competencia(text: str) -> bool | str:
    """Validate a reporting period using the domain period parser.

    The help token is accepted so the calling prompt can display contextual
    guidance instead of treating it as invalid input.
    """
    if text == _HELP_TOKEN:
        return True

    try:
        month_bounds(text)
    except (TypeError, ValueError):
        return "Competência inválida. Use AAAA-MM com um mês entre 01 e 12, por exemplo 2026-06."

    return True


def _validate_non_empty_text(text: str) -> bool | str:
    """Require non-empty text while allowing the contextual-help token."""
    if text == _HELP_TOKEN:
        return True

    if not text.strip():
        return "Informe um valor ou digite '?' para obter ajuda."

    return True


def _ask_with_help(
    provider: InteractionProvider,
    ask: Callable[[], str],
    help_text: str,
) -> str:
    """Ask a free-text or choice question with contextual help.

    The prompt is repeated whenever the provider returns ``?``.

    Args:
        provider: Interaction abstraction used to display help.
        ask: Zero-argument function that performs one prompt attempt.
        help_text: Literal help text displayed after the help token.

    Returns:
        The answer returned by the provider, excluding the help token.
    """
    while True:
        answer = ask()

        if answer == _HELP_TOKEN:
            provider.show_message(
                help_text,
                style="dim",
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
    """Collect a non-empty filesystem path with contextual help.

    The supplied path is expanded for a leading user-home marker but is not
    resolved. Avoiding ``Path.resolve`` prevents collection from requiring the
    path to exist and preserves relative-path behavior.

    Args:
        provider: Interaction abstraction used for the prompt.
        prompt: User-facing question.
        default: Default textual path.
        help_text: Contextual guidance displayed for ``?``.

    Returns:
        The collected path with ``~`` expanded.
    """
    answer = _ask_with_help(
        provider,
        lambda: provider.ask_text(
            prompt,
            default=default,
            validate=_validate_non_empty_text,
        ),
        help_text,
    )

    return Path(answer.strip()).expanduser()


def show_opening(provider: InteractionProvider) -> None:
    """Display the guided-flow introduction."""
    provider.show_message(
        "pyauditor: aferição guiada. Digite '?' nas perguntas de texto "
        "para obter ajuda contextual. Ctrl+C encerra o fluxo; etapas de "
        "processamento já registradas poderão ser retomadas.",
        style="bold cyan",
    )


def collect_answers(
    provider: InteractionProvider,
) -> GuidedAnswers:
    """Collect and confirm the inputs required by the orchestrator.

    Declining confirmation restarts collection with a loop rather than
    recursion, allowing any number of revisions without increasing the call
    stack.

    Args:
        provider: Interaction abstraction used for all questions.

    Returns:
        Confirmed guided-flow answers.
    """
    while True:
        competencia = _ask_with_help(
            provider,
            lambda: provider.ask_text(
                "Competência (AAAA-MM):",
                validate=_validate_competencia,
            ),
            "A competência é o mês de aferição. Use AAAA-MM, por exemplo "
            "2026-06 para junho de 2026.",
        )

        orgao_choice = _ask_with_help(
            provider,
            lambda: provider.ask_choice(
                "Órgão:",
                (
                    "MinC",
                    "MTur",
                    "both: MinC e MTur",
                ),
                default="MinC",
            ),
            "Escolha MinC ou MTur para processar somente um órgão. "
            "Escolha both para executar o plano phase-major dos dois órgãos "
            "e, quando selecionada, a consolidação final.",
        )
        orgao = "both" if orgao_choice.startswith("both") else orgao_choice

        config_dir = _ask_path(
            provider,
            "Diretório de configurações:",
            default="configs",
            help_text=(
                "Diretório raiz que contém _shared ou os diretórios de "
                "configuração específicos de cada órgão."
            ),
        )
        data_dir = _ask_path(
            provider,
            "Diretório de dados:",
            default="input",
            help_text=(
                "Diretório raiz dos dados de entrada, incluindo os "
                "subdiretórios dos órgãos e os arquivos compartilhados."
            ),
        )
        output_dir = _ask_path(
            provider,
            "Diretório de ROMs:",
            default="roms",
            help_text=(
                "Diretório onde measure grava os resumos e demais artefatos "
                "ROM utilizados por report e consolidate."
            ),
        )
        report_dir = _ask_path(
            provider,
            "Diretório de relatórios:",
            default="reports",
            help_text=(
                "Diretório de destino dos relatórios individuais, arquivos "
                "sintéticos e relatório consolidado."
            ),
        )
        capa_path = _ask_path(
            provider,
            "Caminho-base da capa:",
            default="input/capa.csv",
            help_text=(
                "Caminho-base usado para localizar ou criar a capa de cada "
                "órgão. A resolução final é feita pelo helper canônico de "
                "caminhos de capa."
            ),
        )

        answers = GuidedAnswers(
            competencia=competencia,
            orgao=orgao,
            config_dir=config_dir,
            data_dir=data_dir,
            output_dir=output_dir,
            report_dir=report_dir,
            capa_path=capa_path,
        )

        if provider.confirm(
            "Os dados informados estão corretos?",
            default=True,
        ):
            return answers

        provider.show_message(
            "Vamos revisar as informações.",
            style="yellow",
        )


def select_commands(
    provider: InteractionProvider,
    orgao: str,
) -> frozenset[str]:
    """Collect a non-empty set of commands for the selected plan.

    Consolidation is available only for ``both``. The provider may allow the
    user to omit upstream commands when their artifacts already exist; the
    orchestrator remains responsible for checking those dependencies.

    Args:
        provider: Interaction abstraction used for command selection.
        orgao: Confirmed organization selector.

    Returns:
        Non-empty set of selected command identifiers.

    Raises:
        ValueError: If ``orgao`` is not supported.
    """
    if orgao not in {"MinC", "MTur", "both"}:
        raise ValueError(f"Seletor de órgão não suportado: {orgao!r}.")

    labels: Final[dict[str, str]] = {
        "bootstrap": "bootstrap: cria ou atualiza a capa do contrato",
        "split": "split: prepara categorias e gera o arquivo sintético",
        "measure": "measure: apura os indicadores INMS",
        "report": "report: gera o relatório da competência",
        "consolidate": ("consolidate: reúne MinC e MTur no relatório consolidado"),
    }

    consolidate_available = orgao == "both"
    choices: list[tuple[str, str, bool, str | None]] = []

    for command in _ALL_COMMANDS:
        if command == "consolidate":
            choices.append(
                (
                    labels[command],
                    command,
                    consolidate_available,
                    (None if consolidate_available else "disponível somente para both"),
                )
            )
            continue

        choices.append(
            (
                labels[command],
                command,
                True,
                None,
            )
        )

    while True:
        selected = provider.ask_multi_choice(
            "Selecione as etapas:",
            choices,
        )

        if selected:
            return frozenset(selected)

        provider.show_message(
            "Selecione ao menos uma etapa para iniciar a execução.",
            style="yellow",
        )


def _state_presentation(
    entry: CommandStateEntry,
) -> tuple[str, str]:
    """Return the literal marker and style for a command state."""
    return _STATE_PRESENTATION.get(
        entry.status,
        _UNKNOWN_STATE_PRESENTATION,
    )


def _render_state_line(
    entry: CommandStateEntry,
) -> tuple[str, str]:
    """Build a literal status line and its separate presentation style.

    Markup is not embedded in the returned text. This allows providers to
    render command names and organization values literally.

    Args:
        entry: Persisted command-state transition.

    Returns:
        A pair containing the literal status text and provider style.
    """
    icon, style = _state_presentation(entry)
    orgao = entry.orgao or "consolidado"

    return (
        f"{icon} {entry.command} ({orgao})",
        style,
    )


def _force_commands_for(
    orgao: str,
    commands: frozenset[str],
) -> frozenset[str]:
    """Return applicable production commands that require fresh results.

    Report and consolidation are inexpensive to regenerate from materialized
    inputs and provide publication and financial fields required by the final
    summary. Only commands selected by the user and applicable to the current
    organization plan are forced.
    """
    forced: set[str] = set()

    if "report" in commands:
        forced.add("report")

    if orgao == "both" and "consolidate" in commands:
        forced.add("consolidate")

    return frozenset(forced)


def _is_pre_dispatch_failure(
    entry: CommandStateEntry,
) -> bool:
    """Return whether an error was produced by a dependency check.

    The persisted state contract requires timestamps for every ``error``
    transition, including pre-dispatch failures. Until failure stage becomes
    an explicit state field, the orchestrator's controlled dependency-message
    prefix is the canonical discriminator.
    """
    message = entry.error_message or ""
    return message.startswith(_PRE_DISPATCH_FAILURE_PREFIX)


def run_guided_flow(
    provider: InteractionProvider,
) -> int:
    """Run the complete guided flow and translate cancellation to exit 130.

    The provider must translate user cancellation from its underlying UI
    framework into :class:`InteractionCancelled`.

    Args:
        provider: Interaction implementation used by every screen.

    Returns:
        The final run exit code, or 130 when the user cancels.
    """
    try:
        return _run_guided_flow(provider)
    except InteractionCancelled:
        provider.show_message(
            "Execução encerrada pelo usuário. Etapas de processamento já "
            "registradas foram preservadas e poderão ser retomadas.",
            style="yellow",
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
        force_commands=_force_commands_for(
            answers.orgao,
            commands,
        ),
    )

    def on_state_change(
        entry: CommandStateEntry,
    ) -> None:
        """Display one persisted orchestration transition."""
        message, style = _render_state_line(entry)
        provider.show_message(
            message,
            style=style,
        )

    def on_failure(
        entry: CommandStateEntry,
    ) -> FailureDecision:
        """Ask how the orchestrator should handle a command failure."""
        reason = entry.error_message or "falha sem mensagem disponível"
        provider.show_message(
            f"{entry.command} falhou: {reason}",
            style="bold red",
        )

        choices: tuple[str, ...]
        if _is_pre_dispatch_failure(entry):
            choices = (
                "Ignorar esta etapa",
                "Abortar a execução",
            )
        else:
            choices = (
                "Tentar novamente",
                "Ignorar esta etapa",
                "Abortar a execução",
            )

        choice = provider.ask_choice(
            "Como prosseguir?",
            choices,
        )

        if choice.startswith("Tentar"):
            return "retry"

        if choice.startswith("Ignorar"):
            return "skip"

        return "abort"

    run_result = execute_run(
        request,
        on_state_change=on_state_change,
        on_failure=on_failure,
    )
    return provider.show_summary(run_result)
