"""Modelagem do relatório estruturado de conclusão (JSON/telemetria) —
a metade de `orchestration/summary.py` que não depende de Rich (ticket 06
SRP). `summary.py` consome o schema via `summary_json()` e renderiza.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from math import isfinite
from typing import Final, TypedDict

from pyauditor.cli.bootstrap import BootstrapResult
from pyauditor.cli.consolidate import ConsolidateResult
from pyauditor.cli.measure import MeasureResult
from pyauditor.cli.report import ReportResult
from pyauditor.cli.results import exit_code_name
from pyauditor.cli.split import SplitResult
from pyauditor.orchestration.run import RunResult
from pyauditor.orchestration.state import parse_iso_timestamp

__all__: Final[tuple[str, ...]] = (
    "CompletionSummaryJson",
    "summary_json",
)

type JsonNumber = int | float
type CommandResult = (
    BootstrapResult | SplitResult | MeasureResult | ReportResult | ConsolidateResult
)

_RESULT_TYPE_FOR_COMMAND: Final[dict[str, type[CommandResult]]] = {
    "bootstrap": BootstrapResult,
    "split": SplitResult,
    "measure": MeasureResult,
    "report": ReportResult,
    "consolidate": ConsolidateResult,
}


class IndicatorCountJson(TypedDict):
    """Indicator counts reported for one organization."""

    aferidos: int
    total_esperado: int


class OrganizationSummaryJson(TypedDict):
    """Structured financial and publication state for one organization."""

    indicadores: IndicatorCountJson
    glosa: str
    publicable: bool
    motivo_publicacao: str | None
    relatorio_gerado: bool


class ConsolidatedSummaryJson(TypedDict):
    """Structured information about the consolidated report."""

    caminho: str
    decisoes_preservadas: int
    glosa: str
    total_pontos: JsonNumber | str


class PublicationSummaryJson(TypedDict):
    """Structured publication decision for the completed run."""

    liberada: bool
    motivo: str | None


class CompletionSummaryJson(TypedDict):
    """Stable machine-readable completion-summary schema."""

    competencia: str
    resultado: str
    codigo_saida: int
    orgaos: dict[str, OrganizationSummaryJson]
    consolidado: ConsolidatedSummaryJson | None
    publicacao: PublicationSummaryJson
    avisos: int
    erros: int
    duracao_ms: int | None
    caminhos: list[str]


def _result_for(
    *,
    command: str,
    orgao: str | None,
    results: Sequence[object],
) -> CommandResult | None:
    """Return the unique result associated with a command and organization.

    Unknown commands have no registered result type and therefore return
    ``None``. Ambiguous matches also return ``None`` so the renderer can
    report that the result is unavailable without selecting an arbitrary
    artifact.
    """
    expected_type = _RESULT_TYPE_FOR_COMMAND.get(command)
    if expected_type is None:
        return None

    candidates: list[CommandResult] = []

    for result in results:
        if not isinstance(result, expected_type):
            continue

        if command == "consolidate":
            candidates.append(result)
            continue

        if getattr(result, "orgao", None) == orgao:
            candidates.append(result)

    if len(candidates) != 1:
        return None

    return candidates[0]


def _orgaos_no_run(
    run_result: RunResult,
) -> tuple[str, ...]:
    """Return organizations in first-appearance order."""
    seen: set[str] = set()
    ordered: list[str] = []

    for entry in run_result.state.commands:
        if entry.orgao is None or entry.orgao in seen:
            continue

        seen.add(entry.orgao)
        ordered.append(entry.orgao)

    return tuple(ordered)


def _organization_summary(
    run_result: RunResult,
    orgao: str,
) -> OrganizationSummaryJson:
    """Return financial and publication state for one organization."""
    report = _result_for(
        command="report",
        orgao=orgao,
        results=run_result.results,
    )
    measure = _result_for(
        command="measure",
        orgao=orgao,
        results=run_result.results,
    )

    if isinstance(report, ReportResult):
        measured_count = report.indicator_count
        publicable = report.publicable
        glosa_calculada = report.glosa_calculada
        report_generated = True
    else:
        measured_count = len(measure.indicators) if isinstance(measure, MeasureResult) else 0
        publicable = False
        glosa_calculada = False
        report_generated = False

    publication_reason: str | None = None

    if not report_generated:
        publication_reason = f"relatório individual não gerado para {orgao}"
    elif isinstance(report, ReportResult) and not report.publicable:
        publication_reason = (
            f"relatório gerado como rascunho para {orgao}: "
            "campos obrigatórios da capa estão incompletos"
        )

    return {
        "indicadores": {
            "aferidos": measured_count,
            "total_esperado": measured_count,
        },
        "glosa": ("calculada" if glosa_calculada else "não calculada"),
        "publicable": publicable,
        "motivo_publicacao": publication_reason,
        "relatorio_gerado": report_generated,
    }


def _json_number(
    value: object,
    *,
    field: str,
) -> JsonNumber | str:
    """Convert a numeric value into a JSON-safe representation.

    ``Decimal`` values are represented as strings to preserve their exact
    decimal value. Integers and finite floats remain JSON numbers.
    """
    if isinstance(value, bool):
        raise TypeError(f"{field} must not be boolean")

    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError(f"{field} must be finite")
        return format(value, "f")

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError(f"{field} must be finite")
        return value

    raise TypeError(f"{field} must be int, float, or Decimal; received {type(value).__name__}")


def _consolidated_info(run_result: RunResult) -> ConsolidatedSummaryJson | None:
    """Return structured information about the consolidated report."""
    result = _result_for(
        command="consolidate",
        orgao=None,
        results=run_result.results,
    )

    if not isinstance(result, ConsolidateResult):
        return None

    return {
        "caminho": str(result.output_path),
        "decisoes_preservadas": result.decisions_preserved,
        "glosa": ("calculada" if result.glosa_calculada else "não calculada"),
        "total_pontos": _json_number(
            result.total_pontos,
            field="total_pontos",
        ),
    }


def _artifact_paths(run_result: RunResult) -> list[str]:
    """Return unique artifact paths without truncation."""
    paths: list[str] = []
    seen: set[str] = set()

    for result in run_result.results:
        output = getattr(result, "output_path", None)

        if output is None:
            output = getattr(result, "sintetico_path", None)

        if output is None:
            continue

        path = str(output)
        if path in seen:
            continue

        seen.add(path)
        paths.append(path)

    return paths


def _warnings_count(run_result: RunResult) -> int:
    """Count warnings from all command results."""
    total = 0

    for result in run_result.results:
        warnings = getattr(result, "warnings", ())
        if isinstance(warnings, Sequence) and not isinstance(
            warnings,
            str,
        ):
            total += len(warnings)

    return total


def _errors_count(run_result: RunResult) -> int:
    """Count commands that ended in technical error."""
    return sum(1 for entry in run_result.state.commands if entry.status == "error")


def parse_run_timestamp(
    value: str,
    *,
    field: str,
) -> datetime:
    """Parse a timezone-aware ISO 8601 run timestamp."""
    return parse_iso_timestamp(value, field=field)


def _duration_ms(run_result: RunResult) -> int | None:
    """Return the duration of the current orchestration invocation."""
    try:
        started_at = parse_run_timestamp(
            run_result.started_at,
            field="started_at",
        )
        finished_at = parse_run_timestamp(
            run_result.finished_at,
            field="finished_at",
        )
    except (TypeError, ValueError):
        return None

    if finished_at < started_at:
        return None

    return int((finished_at - started_at).total_seconds() * 1000)


def summary_json(run_result: RunResult, exit_code: int) -> CompletionSummaryJson:
    """Build the stable machine-readable completion summary.

    ``run_result`` has the ``RunResult`` contract (competencia, state,
    results, started_at, finished_at) — typed loosely here to keep the JSON
    model decoupled from Rich; ``summary.py`` passes the real object.
    """
    organizations = {
        organization: _organization_summary(
            run_result,
            organization,
        )
        for organization in _orgaos_no_run(run_result)
    }

    publication_reason = next(
        (
            summary["motivo_publicacao"]
            for summary in organizations.values()
            if summary["motivo_publicacao"] is not None
        ),
        None,
    )

    publication_allowed = exit_code == 0

    return {
        "competencia": run_result.competencia,
        "resultado": exit_code_name(exit_code),
        "codigo_saida": exit_code,
        "orgaos": organizations,
        "consolidado": _consolidated_info(run_result),
        "publicacao": {
            "liberada": publication_allowed,
            "motivo": (
                None
                if publication_allowed
                else publication_reason or "etapa final de produção não gerada"
            ),
        },
        "avisos": _warnings_count(run_result),
        "erros": _errors_count(run_result),
        "duracao_ms": _duration_ms(run_result),
        "caminhos": _artifact_paths(run_result),
    }
