"""`pyauditor report <competência>` — consolidate the ROMs `measure` wrote
into the final Excel: `CADASTROS` + `INMS_BASE` + per-group tabs + `GLOSAS`
(spec §6/§13).
"""

import json
from dataclasses import dataclass
from pathlib import Path

from pyauditor.cli.results import DependencyCheck, Status, validate_competencia
from pyauditor.engine.pipeline import discover_configs
from pyauditor.excel.capa import read_capa_fields
from pyauditor.excel.glosas import historico_entry, read_historico, write_historico
from pyauditor.excel.report import build_report, compute_report_glosa
from pyauditor.logging import logger
from pyauditor.rom.summary import IndicatorSummary

HISTORICO_FILENAME = "glosa_historico.json"


@dataclass(frozen=True, slots=True)
class ReportResult:
    status: Status
    competencia: str
    orgao: str
    output_path: Path
    indicator_count: int
    warnings: tuple[str, ...]
    error_message: str | None


def check_report_ready(
    competencia: str, orgao: str, capa_path: Path, roms_dir: Path
) -> DependencyCheck:
    """`report` needs bootstrap's capa and measure's ROMs for this
    (competencia, orgao) — extracted from the ad-hoc checks below."""
    missing: list[str] = []
    if not capa_path.exists():
        missing.append(f"capa ({capa_path}) — rode `pyauditor bootstrap`")
    if not (roms_dir / competencia).is_dir():
        missing.append(
            f"ROMs de {orgao}/{competencia} ({roms_dir / competencia}) — rode `pyauditor measure`"
        )
    return DependencyCheck(satisfied=not missing, missing=tuple(missing))


def _load_summaries(roms_dir: Path) -> list[IndicatorSummary]:
    summaries = []
    for summary_path in sorted(roms_dir.glob("*.json")):
        try:
            raw = json.loads(summary_path.read_text(encoding="utf-8"))
            summaries.append(IndicatorSummary(**raw))
        except (json.JSONDecodeError, TypeError) as exc:
            raise ValueError(f"sumário inválido em {summary_path}: {exc}") from exc
    return summaries


def run_report(
    competencia: str,
    capa_path: Path,
    roms_dir: Path,
    output_path: Path,
    config_dir: Path,
    *,
    expected_orgao: str | None = None,
    is_final_month: bool = False,
) -> ReportResult:
    orgao = expected_orgao or ""

    def _error(message: str) -> ReportResult:
        logger.error(message)
        return ReportResult(
            status="error", competencia=competencia, orgao=orgao, output_path=output_path,
            indicator_count=0, warnings=(), error_message=message,
        )

    competencia_error = validate_competencia(competencia)
    if competencia_error is not None:
        return _error(competencia_error)

    # Defense-in-depth: same checker `cli_main`/the orchestrator call pre-dispatch
    # (ticket "Dependency enforcement") — direct callers that bypass dispatch
    # (tests, future code) still get it.
    dependency_check = check_report_ready(competencia, orgao, capa_path, roms_dir)
    if not dependency_check.satisfied:
        return _error("dependência não satisfeita: " + "; ".join(dependency_check.missing))

    competencia_dir = roms_dir / competencia
    try:
        summaries = _load_summaries(competencia_dir)
    except (OSError, ValueError) as exc:
        return _error(f"falha ao ler sumários de medição em {competencia_dir}: {exc}")

    if not summaries:
        return _error(f"nenhum sumário de medição (.json) encontrado em {competencia_dir}")

    warnings: list[str] = []
    capa_fields = read_capa_fields(capa_path)
    valor_base_raw = capa_fields.get("Valor mensal vigente")
    valor_base = float(valor_base_raw) if isinstance(valor_base_raw, int | float) else None
    if valor_base is None:
        logger.info(
            "capa sem 'Valor mensal vigente' preenchido — GLOSAS terá percentual de ajuste "
            "mas não valor da glosa"
        )

    try:
        configs = discover_configs(config_dir, expected_orgao=expected_orgao)
    except (OSError, ValueError) as exc:
        warning = f"falha ao carregar configs de {config_dir}, CADASTROS será omitido: {exc}"
        logger.warning(warning)
        warnings.append(warning)
        configs = []

    historico_path = roms_dir / HISTORICO_FILENAME
    try:
        historico = read_historico(historico_path)
    except (OSError, json.JSONDecodeError) as exc:
        warning = f"falha ao ler histórico de glosa em {historico_path}, rollover será 0: {exc}"
        logger.warning(warning)
        warnings.append(warning)
        historico = {}

    try:
        build_report(
            competencia, summaries, output_path, valor_base,
            is_final_month=is_final_month, capa_fields=capa_fields,
            configs=configs or None, historico=historico,
        )
    except OSError as exc:
        return _error(f"falha ao escrever {output_path}: {exc}")
    except Exception as exc:  # boundary: never leak a raw traceback past the CLI
        return _error(f"falha inesperada ao montar {output_path}: {exc}")

    try:
        glosa = compute_report_glosa(
            competencia, summaries, valor_base, is_final_month=is_final_month, historico=historico
        )
    except Exception as exc:  # boundary: never leak a raw traceback past the CLI
        return _error(f"falha inesperada ao calcular glosa de {competencia}: {exc}")
    historico[competencia] = historico_entry(competencia, glosa)
    try:
        write_historico(historico_path, historico)
    except OSError as exc:
        warning = f"falha ao gravar histórico de glosa em {historico_path}: {exc}"
        logger.warning(warning)
        warnings.append(warning)

    logger.info(f"relatório consolidado: {output_path} ({len(summaries)} indicadores)")
    return ReportResult(
        status="done", competencia=competencia, orgao=orgao, output_path=output_path,
        indicator_count=len(summaries), warnings=tuple(warnings), error_message=None,
    )
