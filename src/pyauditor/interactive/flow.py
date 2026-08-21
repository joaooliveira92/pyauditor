"""The guided-flow screen sequence (ticket "Guided flow UX screens",
validated as a prototype at `.scratch/interactive-cli/prototype_guided_flow.py`
on branch `prototype/interactive-cli-ux`; ticket "Failure-handling flow" for
retry/skip/abort semantics; ticket "Completion summary and exit codes" for
the final screen). Talks only through the injected `InteractionProvider` —
never imports `rich`/`questionary` directly, and never contains business
logic beyond what screen comes next: sequencing/dependency-checking is
`orchestration.execute_run`'s job.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from pyauditor.interactive.provider import InteractionCancelled, InteractionProvider
from pyauditor.orchestration.run import FailureDecision, RunRequest, execute_run
from pyauditor.orchestration.state import CommandStateEntry

_COMPETENCIA_RE: Final = re.compile(r"^\d{4}-\d{2}$")
_HELP_TOKEN: Final = "?"
_ALL_COMMANDS: Final[tuple[str, ...]] = ("bootstrap", "split", "measure", "report", "consolidate")
_CANCELLED_EXIT_CODE: Final = 130  # Unix convention: 128 + SIGINT(2)

_STATE_ICON: Final[dict[str, tuple[str, str]]] = {
    "pending": ("○", "dim"),
    "running": ("◐", "cyan"),
    "done": ("●", "green"),
    "skipped": ("◌", "yellow"),
    "error": ("✕", "bold red"),
}


@dataclass(frozen=True, slots=True)
class GuidedAnswers:
    competencia: str
    orgao: str
    config_dir: Path
    data_dir: Path
    output_dir: Path
    report_dir: Path
    capa_path: Path


def _validate_competencia(text: str) -> bool | str:
    if text == _HELP_TOKEN:
        return True
    if not _COMPETENCIA_RE.match(text):
        return "Formato esperado: AAAA-MM (ex.: 2026-06). Tente de novo."
    return True


def _ask_with_help(provider: InteractionProvider, ask: object, help_text: str) -> str:
    while True:
        assert callable(ask)
        answer = ask()
        if answer == _HELP_TOKEN:
            provider.show_message(help_text, style="dim")
            continue
        return str(answer)


def show_opening(provider: InteractionProvider) -> None:
    provider.show_message(
        "pyauditor — aferição guiada. Digite '?' em qualquer pergunta para "
        "ajuda contextual. Ctrl+C encerra sem perder o preenchido — a "
        "próxima execução retoma daqui.",
        style="bold cyan",
    )


def collect_answers(provider: InteractionProvider) -> GuidedAnswers:
    # A `while` loop, not recursion — a declined confirmation re-collects any
    # number of times without growing the call stack.
    while True:
        competencia = _ask_with_help(
            provider,
            lambda: provider.ask_text(
                "Competência (AAAA-MM):", validate=_validate_competencia
            ),
            "A competência é o mês de aferição — nomeia os arquivos de entrada e saída. "
            "Ex.: '2026-06' para junho de 2026.",
        )

        orgao_choice = _ask_with_help(
            provider,
            lambda: provider.ask_choice(
                "Órgão:", ["MinC", "MTur", "both — os dois, sequencial"], default="MinC"
            ),
            "'both' roda a cadeia inteira para MinC e depois para MTur, sem cruzar dados.",
        )
        orgao = "both" if orgao_choice.startswith("both") else orgao_choice

        config_dir = Path(provider.ask_text("Diretório de configs:", default="configs"))
        data_dir = Path(provider.ask_text("Diretório de dados:", default="input"))
        output_dir = Path(provider.ask_text("Diretório de ROMs:", default="roms"))
        report_dir = Path(provider.ask_text("Diretório de relatórios:", default="reports"))
        capa_path = Path(
            provider.ask_text("Caminho do capa comum (capa.csv):", default="input/capa.csv")
        )

        answers = GuidedAnswers(
            competencia, orgao, config_dir, data_dir, output_dir, report_dir, capa_path
        )

        if provider.confirm("Está correto?", default=True):
            return answers
        provider.show_message("Vamos revisar.", style="yellow")


def select_commands(provider: InteractionProvider, orgao: str) -> frozenset[str]:
    consolidate_available = orgao == "both"
    labels = {
        "bootstrap": "bootstrap — cria a capa do contrato",
        "split": "split — gera CSV+config por Categoria",
        "measure": "measure — apura os indicadores INMS",
        "report": "report — monta o relatório da competência",
        "consolidate": "consolidate — funde MinC+MTur na planilha financeira",
    }
    choices: list[tuple[str, str, bool, str | None]] = []
    for command in _ALL_COMMANDS:
        if command == "consolidate":
            disabled = None if consolidate_available else "requer --orgao both"
            choices.append((labels[command], command, consolidate_available, disabled))
        else:
            choices.append((labels[command], command, True, None))
    selected = provider.ask_multi_choice("Selecione as etapas:", choices)
    return frozenset(selected) if selected else frozenset()


def _render_state_line(entry: CommandStateEntry) -> str:
    icon, style = _STATE_ICON[entry.status]
    orgao = entry.orgao or "consolidado"
    return f"[{style}]{icon}[/{style}] {entry.command} ({orgao})"


def run_guided_flow(provider: InteractionProvider) -> int:
    try:
        return _run_guided_flow(provider)
    except InteractionCancelled:
        provider.show_message(
            "Encerrado — nada do que já foi preenchido/executado foi perdido; "
            "a próxima execução retoma daqui.",
            style="yellow",
        )
        return _CANCELLED_EXIT_CODE


def _run_guided_flow(provider: InteractionProvider) -> int:
    show_opening(provider)
    answers = collect_answers(provider)
    commands = select_commands(provider, answers.orgao)

    request = RunRequest(
        competencia=answers.competencia,
        orgao=answers.orgao,
        config_dir=answers.config_dir,
        data_dir=answers.data_dir,
        output_dir=answers.output_dir,
        report_dir=answers.report_dir,
        capa_path=answers.capa_path,
        commands=commands,
        force_commands=frozenset({"report", "consolidate"}),
    )

    def on_state_change(entry: CommandStateEntry) -> None:
        provider.show_message(_render_state_line(entry))

    def on_failure(entry: CommandStateEntry) -> FailureDecision:
        # Pre-dispatch dependency failures never ran the Command — no "retry"
        # (repeating a deterministic check is pointless, ticket
        # "Failure-handling flow"). Post-dispatch failures get all three.
        pre_dispatch = entry.started_at is None
        reason = entry.error_message or "falha desconhecida"
        provider.show_message(f"{entry.command} falhou: {reason}", style="bold red")
        choices = (
            ["Ignorar esta etapa", "Abortar a execução"]
            if pre_dispatch
            else ["Tentar novamente", "Ignorar esta etapa", "Abortar a execução"]
        )
        choice = provider.ask_choice("Como prosseguir?", choices)
        if choice.startswith("Tentar"):
            return "retry"
        if choice.startswith("Ignorar"):
            return "skip"
        return "abort"

    run_result = execute_run(request, on_state_change=on_state_change, on_failure=on_failure)
    return provider.show_summary(run_result)
