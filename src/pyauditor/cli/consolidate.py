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

Migração das capas para CSV (ticket 07): os campos comuns vêm de `capa.csv`
e o valor monetário de `objetos.csv` — a capa não carrega mais valores.
Competência/períodos/responsáveis idem (spec competencia-cli-equipe §4/§6):
períodos derivados do argumento da CLI e responsáveis de `equipe.csv`.
"""

from dataclasses import dataclass
from pathlib import Path

from pyauditor.atomic_write import atomic_write
from pyauditor.cli.results import WRITE_FAILURE_HINT, DependencyCheck, Status, validate_competencia
from pyauditor.excel.capa import read_capa_csv_fields
from pyauditor.excel.consolidate import build_consolidated_workbook, read_existing_decisions
from pyauditor.excel.equipe import EQUIPE_FILENAME, read_responsaveis
from pyauditor.logging import log_event, logger
from pyauditor.periodo import month_bounds
from pyauditor.rom.loading import load_summaries, read_valor_base

_ORGAOS: tuple[str, str] = ("MinC", "MTur")


@dataclass(frozen=True, slots=True)
class ConsolidateResult:
    status: Status
    competencia: str  # sem orgao — consolidate é agnóstico de órgão
    output_path: Path
    decisions_preserved: int
    warnings: tuple[str, ...]
    error_message: str | None
    glosa_calculada: bool = True
    total_pontos: float = 0.0


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


def _load_common_capa(data_dir: Path, warnings: list[str]) -> dict[str, object]:
    """Campos comuns do contrato de `capa.csv` (ticket 07). Ausente/malformado
    é dado incompleto — o consolidado é montado mesmo assim, com a capa
    truncada (não bloqueia; a criticidade é do ticket 02/03)."""
    path = data_dir / "capa.csv"
    if not path.exists():
        warnings.append(
            f"capa.csv não encontrado em {data_dir} — capa do consolidado sem campos comuns"
        )
        return {}
    try:
        return read_capa_csv_fields(path)  # type: ignore[return-value]
    except (OSError, ValueError) as exc:
        warnings.append(f"falha ao ler capa.csv em {data_dir}: {exc} — campos comuns ausentes")
        return {}


def run_consolidate(
    competencia: str,
    report_dir: Path,
    roms_dir: Path,
    output_path: Path,
    data_dir: Path | None = None,
) -> ConsolidateResult:
    data_dir = data_dir or report_dir.parent

    def _error(message: str) -> ConsolidateResult:
        logger.error(message)
        return ConsolidateResult(
            status="error",
            competencia=competencia,
            output_path=output_path,
            decisions_preserved=0,
            warnings=(),
            error_message=message,
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

    roms_dirs = {orgao: roms_dir / orgao / competencia for orgao in _ORGAOS}

    try:
        minc = load_summaries(roms_dirs["MinC"])
        mtur = load_summaries(roms_dirs["MTur"])
    except (OSError, ValueError) as exc:
        return _error(f"falha ao ler sumários de medição: {exc}")

    if not minc or not mtur:
        return _error("nenhum sumário de medição (.json) encontrado para um dos órgãos")

    warnings: list[str] = []
    capa = _load_common_capa(data_dir, warnings)
    try:
        valor_base, itens = read_valor_base(data_dir, warnings)
    except ValueError as exc:
        return _error(str(exc))  # Q5: malformado é FALHA (exit 1)

    # §4/§6 — períodos derivados da CLI; responsáveis de equipe.csv com
    # degrade para warning (dado incompleto nunca bloqueia o consolidado).
    periodo = month_bounds(competencia)
    responsaveis, avisos_equipe = read_responsaveis(data_dir / EQUIPE_FILENAME)
    warnings.extend(avisos_equipe)

    try:
        existing_decisions = read_existing_decisions(output_path)
    except Exception as exc:  # boundary: corrupt/hand-edited workbook, never leak a raw traceback
        return _error(f"falha ao ler workbook Excel: {exc}")

    if existing_decisions:
        log_event(
            "decisoes_preservadas",
            f"{len(existing_decisions)} decisão(ões) do fiscal preservada(s)",
            "INFO",
            arquivo=str(output_path),
            quantidade=len(existing_decisions),
        )

    try:
        result = build_consolidated_workbook(
            competencia,
            minc,
            mtur,
            capa,
            existing_decisions,
            valor_base=valor_base,
            itens=itens,
            periodo=periodo,
            responsaveis=responsaveis,
        )
    except Exception as exc:  # boundary: never leak a raw traceback past the CLI
        return _error(f"falha inesperada ao montar consolidado de {competencia}: {exc}")

    try:
        atomic_write(output_path, result.workbook.save)
    except OSError as exc:
        return _error(f"falha ao escrever {output_path}: {exc} — {WRITE_FAILURE_HINT}")
    finally:
        result.workbook.close()

    log_event(
        "consolidate_generated",
        "consolidado gerado",
        "INFO",
        arquivo=str(output_path),
        total_pontos=f"{result.total_pontos:.2f}",
        glosa="não calculada" if not result.glosa_calculada else f"{result.glosa_final:.2f}",
    )
    return ConsolidateResult(
        status="done",
        competencia=competencia,
        output_path=output_path,
        decisions_preserved=len(existing_decisions),
        warnings=tuple(warnings),
        error_message=None,
        glosa_calculada=result.glosa_calculada,
        total_pontos=result.total_pontos,
    )
