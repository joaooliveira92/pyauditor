"""`render_summary()` — the one shared completion-summary renderer (ticket
"Completion summary and exit codes", .scratch/interactive-cli map), used
identically by `cli/run.py` (non-interactive) and `interactive/provider.py`
(`show_summary` just delegates here). Pure output — no prompting — so it
uses `rich.Console` directly rather than the `InteractionProvider` Protocol.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Any, Literal

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from pyauditor.cli.bootstrap import BootstrapResult
from pyauditor.cli.consolidate import ConsolidateResult
from pyauditor.cli.measure import MeasureResult
from pyauditor.cli.report import ReportResult
from pyauditor.cli.results import exit_code_name, is_production_command
from pyauditor.orchestration.run import RunResult, dependency_missing
from pyauditor.orchestration.state import CommandStateEntry

type OutputFormat = Literal["text", "json"]

# ASCII-only markers: the status column is printed to a possibly cp1252-coded
# Windows console (rich falls back to legacy_windows_render there), where any
# non-ASCII glyph would raise UnicodeEncodeError and take the whole `run` down
# with it. Colours still distinguish states on capable terminals.
_STATE_ICON: dict[str, tuple[str, str]] = {
    "pending": ("[ ]", "dim"),
    "running": ("[>]", "cyan"),
    "done": ("[x]", "green"),
    "skipped": ("[~]", "yellow"),
    "error": ("[!]", "bold red"),
}


def exit_code_for_run(
    state_commands: tuple[CommandStateEntry, ...], results: Sequence[object]
) -> int:
    """Contrato de códigos de saída (ticket "03 - Contrato de códigos de
    saída", .scratch/ajuste-cli) para o `run` agregado — precedência
    `1 > 4 > 3 > 0`, agregado por órgão com o pior vencendo:

    - `1` se qualquer Command terminou `error` (falha técnica);
    - `4` se algum report/consolidate sinaliza glosa não calculada;
    - `3` se alguma etapa de produção (`report`/`consolidate`) terminou
      `skipped` — resultado financeiro incompleto nunca vale `0` (revisão do
      `skipped jamais é falha` do mapa interactive-cli) — ou se algum
      resultado é não-publicável (rascunho, ticket 02);
    - `0` caso contrário.
    """
    if any(entry.status == "error" for entry in state_commands):
        return 1
    if any(getattr(result, "glosa_calculada", True) is False for result in results):
        return 4
    if any(
        entry.status == "skipped" and is_production_command(entry.command)
        for entry in state_commands
    ):
        return 3
    if any(getattr(result, "publicable", True) is False for result in results):
        return 3
    return 0


_RESULT_TYPE_FOR_COMMAND: dict[str, type] = {
    "bootstrap": BootstrapResult,
    "measure": MeasureResult,
    "report": ReportResult,
    "consolidate": ConsolidateResult,
}


def _result_for(entry: CommandStateEntry, results: tuple[object, ...]) -> object | None:
    expected_type = _RESULT_TYPE_FOR_COMMAND[entry.command]
    for result in results:
        if not isinstance(result, expected_type):
            continue
        if entry.command == "consolidate" or getattr(result, "orgao", None) == entry.orgao:
            return result
    return None


def _bootstrap_artifact(result: BootstrapResult) -> str:
    return str(result.capa_path)


def _measure_artifact(result: MeasureResult) -> str:
    failing = [i.contractual_id for i in result.indicators if i.hard_failure]
    line = f"{len(result.indicators)} indicador(es) apurado(s)"
    if failing:
        line += f" — falhas: {', '.join(failing)}"
    return line


def _report_artifact(result: ReportResult) -> str:
    return f"{result.output_path} ({result.indicator_count} indicadores)"


def _consolidate_artifact(result: ConsolidateResult) -> str:
    return f"{result.output_path} ({result.decisions_preserved} decisão(ões) preservada(s))"


# Keyed the same way as `_RESULT_TYPE_FOR_COMMAND` — one type-discrimination
# point instead of two (a prior isinstance-chain here re-decided the same
# "which CommandResult subtype is this" question `_result_for` already answered).
_ARTIFACT_FORMATTER_FOR_TYPE: dict[type, Callable[[Any], str]] = {
    BootstrapResult: _bootstrap_artifact,
    MeasureResult: _measure_artifact,
    ReportResult: _report_artifact,
    ConsolidateResult: _consolidate_artifact,
}


def _artifact_line(entry: CommandStateEntry, result: object | None) -> str:
    if result is None:
        return "pulado" if entry.status == "skipped" else "—"
    formatter = _ARTIFACT_FORMATTER_FOR_TYPE.get(type(result))
    return formatter(result) if formatter is not None else "—"


def _next_steps(run_result: RunResult) -> list[str]:
    steps: list[str] = []
    for entry in run_result.state.commands:
        if entry.status == "done":
            continue
        missing = dependency_missing(entry.command, entry.orgao, run_result.request)
        if missing:
            steps.append(f"{entry.command} ({entry.orgao or '—'}): {', '.join(missing)}")
    return steps


def _result_for_command(
    run_result: RunResult, command: str, orgao: str | None = None
) -> object | None:
    """Desambigua por `CommandStateEntry`; aqui simulamos a entrada de um
    comando que sabemos ter rodado para achar o resultado."""
    entry = CommandStateEntry(command=command, orgao=orgao, status="done")
    return _result_for(entry, run_result.results)


def _orgaos_no_run(run_result: RunResult) -> tuple[str, ...]:
    """Órgãos presentes no run, na ordem em que aparecem no estado."""
    seen: list[str] = []
    for entry in run_result.state.commands:
        if entry.orgao and entry.orgao not in seen:
            seen.append(entry.orgao)
    return tuple(seen)


def _sumario_orgao(run_result: RunResult, orgao: str) -> dict[str, Any]:
    """Estado financeiro/publicable por órgão (tickets 01/02) — os mesmos
    sinais que `exit_code_for_run` lê."""
    report = _result_for_command(run_result, "report", orgao)
    measure = _result_for_command(run_result, "measure", orgao)
    if isinstance(report, ReportResult):
        aferidos = report.indicator_count
        publicable = report.publicable
        glosa_calc = report.glosa_calculada
    else:
        aferidos = len(measure.indicators) if isinstance(measure, MeasureResult) else 0
        publicable = True
        glosa_calc = True
    motivo: str | None = None
    if isinstance(report, ReportResult) and not report.publicable:
        motivo = (
            f"relatório gerado como rascunho — capa incompleta em {orgao} "
            "(obrigatórios para publicar ausentes)"
        )
    # `total_esperado` acompanha `aferidos` até a névoa "Validação de
    # indicadores" (nº esperado = 14?) graduar — contratos estável pros CI.
    return {
        "indicadores": {"aferidos": aferidos, "total_esperado": aferidos},
        "glosa": "calculada" if glosa_calc else "não calculada",
        "publicable": publicable,
        "motivo_publicacao": motivo,
    }


def _consolidado_info(run_result: RunResult) -> dict[str, Any] | None:
    csol = _result_for_command(run_result, "consolidate")
    if not isinstance(csol, ConsolidateResult):
        return None
    return {
        "caminho": str(csol.output_path),
        "decisoes_preservadas": csol.decisions_preserved,
        "glosa": "calculada" if csol.glosa_calculada else "não calculada",
    }


def _caminhos_artefatos(run_result: RunResult) -> list[str]:
    """Caminhos completos dos artefatos — sem truncamento (revisão §7)."""
    paths: list[str] = []
    for result in run_result.results:
        output = getattr(result, "output_path", None)
        if output is not None:
            paths.append(str(output))
    return list(dict.fromkeys(paths))


def _warnings_count(run_result: RunResult) -> int:
    return sum(len(getattr(result, "warnings", ())) for result in run_result.results)


def _errors_count(run_result: RunResult) -> int:
    return sum(1 for entry in run_result.state.commands if entry.status == "error")


def _duracao_ms(run_result: RunResult) -> int:
    """Duração da execução pelo relógio de parede do estado: do menor
    `started_at` ao maior `finished_at` entre os Commands. `0` se o estado
    não tiver timestamps (ex.: resultados sintéticos de teste)."""
    stamps: list[datetime] = []
    for entry in run_result.state.commands:
        if entry.started_at is not None:
            stamps.append(datetime.fromisoformat(entry.started_at))
        if entry.finished_at is not None:
            stamps.append(datetime.fromisoformat(entry.finished_at))
    if len(stamps) < 2:
        return 0
    return max(0, int((max(stamps) - min(stamps)).total_seconds() * 1000))


def summary_json(run_result: RunResult, exit_code: int) -> dict[str, Any]:
    """Saída estruturada para automação (Q5/Q9/Q10, ticket 04) — mesmo
    estado global do código de saída. Nomes estáveis em pt-BR; números (ms)
    e caminhos completos para consumo por CI/workers."""
    orgaos = {
        orgao: _sumario_orgao(run_result, orgao)
        for orgao in _orgaos_no_run(run_result)
    }
    motivo_publicacao = next(
        (v["motivo_publicacao"] for v in orgaos.values() if v["motivo_publicacao"]), None
    )
    liberada = exit_code == 0
    return {
        "competencia": run_result.competencia,
        "resultado": exit_code_name(exit_code),
        "codigo_saida": exit_code,
        "orgaos": orgaos,
        "consolidado": _consolidado_info(run_result),
        "publicacao": {
            "liberada": liberada,
            "motivo": None if liberada else motivo_publicacao
            or "etapa final de produção não gerada",
        },
        "avisos": _warnings_count(run_result),
        "erros": _errors_count(run_result),
        "duracao_ms": _duracao_ms(run_result),
        "caminhos": _caminhos_artefatos(run_result),
    }


def _painel_resultado(run_result: RunResult, exit_code: int) -> Panel:
    """Painel "Resultado" — o estado global inequívoco (Q3/Q9/Q10)."""
    orgaos = {
        orgao: _sumario_orgao(run_result, orgao) for orgao in _orgaos_no_run(run_result)
    }
    indicadores = ", ".join(
        f"{orgao} {d['indicadores']['aferidos']}/{d['indicadores']['total_esperado']}"
        for orgao, d in orgaos.items()
    )
    rascunhos = [orgao for orgao, d in orgaos.items() if not d["publicable"]]
    relatorios = f"{len(orgaos)}"
    if rascunhos:
        plural = "s" if len(rascunhos) > 1 else ""
        relatorios += f" ({len(rascunhos)} rascunho{plural} — {', '.join(rascunhos)})"

    estados_glosa = {d["glosa"] for d in orgaos.values()}
    glosa = (
        "sem glosa"
        if not estados_glosa
        else ("não calculada" if "não calculada" in estados_glosa else "calculada")
    )

    if exit_code == 0:
        publicacao = "liberada"
    elif exit_code == 4:
        publicacao = "bloqueada — cálculo financeiro indisponível"
    elif exit_code == 3:
        motivo = next(
            (d["motivo_publicacao"] for d in orgaos.values() if d["motivo_publicacao"]),
            None,
        )
        publicacao = f"bloqueada — {motivo}" if motivo else "bloqueada — etapa final não gerada"
    else:
        publicacao = "não informada (falha técnica)"

    linhas = [
        f"[bold]Resultado:[/bold] {exit_code_name(exit_code)}",
        f"[bold]Competência:[/bold] {run_result.competencia}",
        f"[bold]Órgãos processados:[/bold] {len(orgaos)}",
        f"[bold]Indicadores apurados:[/bold] {indicadores}",
        f"[bold]Relatórios individuais:[/bold] {relatorios}",
        "[bold]Relatório consolidado:[/bold] "
        + ("gerado" if _consolidado_info(run_result) else "não gerado"),
        f"[bold]Avisos:[/bold] {_warnings_count(run_result)}",
        f"[bold]Erros:[/bold] {_errors_count(run_result)}",
        f"[bold]Glosa monetária:[/bold] {glosa}",
        f"[bold]Publicação:[/bold] {publicacao}",
        f"[bold]Duração:[/bold] {_duracao_ms(run_result) / 1000:.2f} s",
    ]
    return Panel("\n".join(linhas), title="Resultado", border_style="white")


def render_summary(
    run_result: RunResult,
    *,
    log_path: object | None = None,
    output: OutputFormat = "text",
    console: Console | None = None,
) -> None:
    """Resumo final de uma execução (ticket "04 - Resumo final acionável").

    - `output="text"`: tabela de etapas + painel Resultado + bloco Artefatos
      (caminhos completos) + log + próximos passos — para humano.
    - `output="json"`: só a saída estruturada (mesmo estado global do código
      de saída) — para automação; nada de rich na stdout.
    """
    console = console or Console()
    code = exit_code_for_run(run_result.state.commands, run_result.results)

    if output == "json":
        console.print_json(json.dumps(summary_json(run_result, code), ensure_ascii=False))
        return

    table = Table(box=None, show_header=True, header_style="bold")
    table.add_column("")
    table.add_column("Command")
    table.add_column("Órgão")
    table.add_column("Artefatos / avisos")

    for entry in run_result.state.commands:
        icon, style = _STATE_ICON[entry.status]
        result = _result_for(entry, run_result.results)
        detail = entry.error_message or _artifact_line(entry, result)
        if isinstance(result, ReportResult) and not result.publicable:
            detail += " [dim](rascunho — não publicável)[/dim]"
        table.add_row(f"[{style}]{icon}[/{style}]", entry.command, entry.orgao or "—", detail)

    console.print(table)
    console.print(_painel_resultado(run_result, code))

    caminhos = _caminhos_artefatos(run_result)
    if caminhos:
        linhas_artefatos = "\n".join(f"  • {path}" for path in caminhos)
        console.print(Panel(linhas_artefatos, title="Artefatos", border_style="cyan"))

    if log_path is not None:
        console.print(f"[dim]Log completo: {log_path}[/dim]")

    steps = _next_steps(run_result)
    if steps:
        console.print(Panel("\n".join(steps), title="Próximos passos", border_style="cyan"))
