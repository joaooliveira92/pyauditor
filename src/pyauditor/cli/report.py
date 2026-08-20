"""`pyauditor report <competência>` — consolidate the ROMs `measure` wrote
into the final Excel: `CADASTROS` + `INMS_BASE` + per-group tabs + `GLOSAS`
(spec §6/§13).
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from pyauditor.cli.results import DependencyCheck, Status, validate_competencia
from pyauditor.engine.pipeline import discover_configs
from pyauditor.excel.capa import read_capa_fields
from pyauditor.excel.glosas import historico_entry, read_historico, write_historico
from pyauditor.excel.report import build_report, compute_report_glosa
from pyauditor.logging import log_event, logger
from pyauditor.rom.summary import IndicatorSummary

HISTORICO_FILENAME = "glosa_historico.json"

# Obrigatórios para publicar/assinar (ticket "02 - Criticidade dos campos da
# capa"): ausentes → relatório vira rascunho (não-publicável), o que o código
# de saída 3 reflete. Monetários ficam fora — saem da capa (ticket 07); a
# ausência de valor é "glosa não calculada" (ticket 01 → código 4).
_PUBLICATION_FIELDS: Final[tuple[str, ...]] = (
    "Período inicial da aferição",
    "Período final da aferição",
    "Fiscal técnico",
    "Fiscal requisitante",
    "Fiscal administrativo",
    "Gestor do contrato",
)


def missing_publication_fields(capa_fields: dict[str, object]) -> tuple[str, ...]:
    """Campos `_PUBLICATION_FIELDS` vazios/ausentes na capa — o conjunto de
    "pendências impeditivas" que o código 3 mapeia. A Situação ≠ "Em
    preenchimento" também bloqueia publicação (ticket 02), mas não entra na
    contagem por campo: é um gate à parte avaliado pelo chamador."""
    return tuple(
        label for label in _PUBLICATION_FIELDS if not str(capa_fields.get(label, "")).strip()
    )


@dataclass(frozen=True, slots=True)
class ReportResult:
    status: Status
    competencia: str
    orgao: str
    output_path: Path
    indicator_count: int
    warnings: tuple[str, ...]
    error_message: str | None
    publicable: bool = True
    glosa_calculada: bool = True


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
    try:
        capa_fields = read_capa_fields(capa_path)
    except Exception as exc:  # boundary: corrupt/hand-edited workbook, never leak a raw traceback
        return _error(f"falha ao ler capa em {capa_path}: {exc}")
    valor_base_raw = capa_fields.get("Valor mensal vigente")
    valor_base = float(valor_base_raw) if isinstance(valor_base_raw, int | float) else None
    if valor_base is None:
        log_event(
            "glosa_nao_calculada",
            "glosa monetária não calculada",
            "WARNING",
            orgao=orgao,
            motivo="valor mensal ausente na capa",
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

    situacao = str(capa_fields.get("Situação geral da aferição", "")).strip()
    publicable = not missing_publication_fields(capa_fields) and situacao != "Em preenchimento"
    log_event(
        "report_generated",
        f"relatório gerado: {output_path} ({len(summaries)} indicadores)",
        "INFO",
        orgao=orgao,
        arquivo=str(output_path),
        status="rascunho" if not publicable else "publicavel",
    )
    return ReportResult(
        status="done", competencia=competencia, orgao=orgao, output_path=output_path,
        indicator_count=len(summaries), warnings=tuple(warnings), error_message=None,
        publicable=publicable, glosa_calculada=valor_base is not None,
    )
