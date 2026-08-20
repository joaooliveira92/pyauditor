"""`pyauditor consolidate <competência>` — fuses the MinC and MTur per-órgão
reports into the consolidated financial workbook (spec: .scratch/multi-org-
pipeline map, "Pipeline multi-órgão", tickets 01/02/04).

Never re-runs `measure`/`report`: requires both
`reports/relatorio_<comp>_MinC.xlsx` and `_MTur.xlsx` to already exist
(ticket 04 Q1) — errors naming whichever is missing rather than generating
it. Re-running `consolidate` over an already-decorated
`relatorio_<comp>_consolidado.xlsx` merges: recomputed fields refresh, the
fiscal's decision columns (Justificativa/Decisão Fiscal/Observação) are
preserved (ticket 04 Q3).
"""

import json
from dataclasses import dataclass
from pathlib import Path

from pyauditor.atomic_write import atomic_write
from pyauditor.cli.results import DependencyCheck, Status, validate_competencia
from pyauditor.excel.capa import read_capa_fields
from pyauditor.excel.consolidate import build_consolidated_workbook, read_existing_decisions
from pyauditor.logging import logger
from pyauditor.rom.summary import IndicatorSummary

_ORGAOS: tuple[str, str] = ("MinC", "MTur")


@dataclass(frozen=True, slots=True)
class ConsolidateResult:
    status: Status
    competencia: str  # sem orgao — consolidate é agnóstico de órgão
    output_path: Path
    decisions_preserved: int
    warnings: tuple[str, ...]
    error_message: str | None


def check_consolidate_ready(competencia: str, report_dir: Path, roms_dir: Path) -> DependencyCheck:
    """`consolidate` needs both MinC and MTur `report` outputs (and their
    ROMs) — the pair is fixed, not a generic per-orgao predecessor."""
    missing: list[str] = []
    report_paths = {
        orgao: report_dir / f"relatorio_{competencia}_{orgao}.xlsx" for orgao in _ORGAOS
    }
    missing.extend(str(path) for path in report_paths.values() if not path.exists())
    roms_dirs = {orgao: roms_dir / orgao / competencia for orgao in _ORGAOS}
    missing.extend(str(d) for d in roms_dirs.values() if not d.is_dir())
    return DependencyCheck(satisfied=not missing, missing=tuple(missing))


def _load_summaries(roms_dir: Path) -> list[IndicatorSummary]:
    summaries: list[IndicatorSummary] = []
    for summary_path in sorted(roms_dir.glob("*.json")):
        try:
            raw = json.loads(summary_path.read_text(encoding="utf-8"))
            summaries.append(IndicatorSummary(**raw))
        except (json.JSONDecodeError, TypeError) as exc:
            raise ValueError(f"sumário inválido em {summary_path}: {exc}") from exc
    return summaries


def run_consolidate(
    competencia: str,
    report_dir: Path,
    roms_dir: Path,
    output_path: Path,
) -> ConsolidateResult:
    def _error(message: str) -> ConsolidateResult:
        logger.error(message)
        return ConsolidateResult(
            status="error", competencia=competencia, output_path=output_path,
            decisions_preserved=0, warnings=(), error_message=message,
        )

    competencia_error = validate_competencia(competencia)
    if competencia_error is not None:
        return _error(competencia_error)

    # Defense-in-depth: same checker `cli_main`/the orchestrator call pre-dispatch
    # (ticket "Dependency enforcement") — direct callers that bypass dispatch
    # (tests, future code) still get it.
    dependency_check = check_consolidate_ready(competencia, report_dir, roms_dir)
    if not dependency_check.satisfied:
        return _error("dependência não satisfeita: " + "; ".join(dependency_check.missing))

    report_paths = {
        orgao: report_dir / f"relatorio_{competencia}_{orgao}.xlsx" for orgao in _ORGAOS
    }
    roms_dirs = {orgao: roms_dir / orgao / competencia for orgao in _ORGAOS}

    try:
        minc = _load_summaries(roms_dirs["MinC"])
        mtur = _load_summaries(roms_dirs["MTur"])
    except (OSError, ValueError) as exc:
        return _error(f"falha ao ler sumários de medição: {exc}")

    if not minc or not mtur:
        return _error("nenhum sumário de medição (.json) encontrado para um dos órgãos")

    try:
        minc_capa = read_capa_fields(report_paths["MinC"])
        mtur_capa = read_capa_fields(report_paths["MTur"])
        existing_decisions = read_existing_decisions(output_path)
    except Exception as exc:  # boundary: corrupt/hand-edited workbook, never leak a raw traceback
        return _error(f"falha ao ler workbook Excel: {exc}")

    if existing_decisions:
        logger.info(
            f"{len(existing_decisions)} decisão(ões) do fiscal preservada(s) de {output_path}"
        )

    try:
        result = build_consolidated_workbook(
            competencia, minc, mtur, minc_capa, mtur_capa, existing_decisions
        )
    except Exception as exc:  # boundary: never leak a raw traceback past the CLI
        return _error(f"falha inesperada ao montar consolidado de {competencia}: {exc}")

    try:
        atomic_write(output_path, result.workbook.save)
    except OSError as exc:
        return _error(f"falha ao escrever {output_path}: {exc}")
    finally:
        result.workbook.close()

    logger.info(
        f"relatório consolidado: {output_path} "
        f"(total de pontos: {result.total_pontos:.2f}, glosa: {result.glosa_final:,.2f})"
    )
    return ConsolidateResult(
        status="done", competencia=competencia, output_path=output_path,
        decisions_preserved=len(existing_decisions), warnings=(), error_message=None,
    )
