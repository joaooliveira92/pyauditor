"""`pyauditor report <competência>` — consolidate the ROMs `measure` wrote
into the final Excel: `CAPA_E_CONTROLE` + `CADASTROS` + `INMS_BASE` +
per-group tabs + `GLOSAS` (spec §6/§13).

Migração das capas para CSV (ticket 07): a capa é `capa.csv` (campos comuns)
+ `capa_{orgao}.csv` (campos por órgão), e o valor monetário vem de
`objetos.csv`. A capa pode estar incompleta — processa e marca rascunho
(ticket 02); `objetos.csv` ausente significa glosa não calculada (ticket 01),
malformado é falha técnica (ticket 07 Q5). Competência/período divergentes
ou fora do formato `DD/MM/AAAA` são WARNING, nunca falha técnica (ticket 10).
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from pyauditor.cli.results import WRITE_FAILURE_HINT, DependencyCheck, Status, validate_competencia
from pyauditor.engine.pipeline import discover_configs
from pyauditor.excel.capa import read_capa_csv_fields, validate_periodo_competencia
from pyauditor.excel.glosas import historico_entry, read_historico, write_historico
from pyauditor.excel.objetos import OBJETOS_FILENAME, read_objetos
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
    competencia: str, orgao: str, capa_path: Path, roms_dir: Path, data_dir: Path | None = None
) -> DependencyCheck:
    """`report` precisa das capas CSV (comum + por órgão) e dos ROMs de
    `measure`. `capa_path` é a capa comum (`capa.csv`); a do órgão fica ao
    lado (`capa_{orgao}.csv`)."""
    missing: list[str] = []
    if not capa_path.exists():
        missing.append(f"capa comum ({capa_path}) — rode `pyauditor bootstrap`")
    orgao_capa = capa_path.parent / f"capa_{orgao}.csv"
    if not orgao_capa.exists():
        missing.append(f"capa de {orgao} ({orgao_capa}) — rode `pyauditor bootstrap`")
    if not (roms_dir / competencia).is_dir():
        missing.append(
            f"ROMs de {orgao}/{competencia} ({roms_dir / competencia}) — rode `pyauditor measure`"
        )
    return DependencyCheck(satisfied=not missing, missing=tuple(missing))


def _load_summaries(roms_dir: Path) -> list[IndicatorSummary]:
    # orgao esperado vem do diretório roms/<orgao>/<competencia> — cross-check contra sidecar
    expected_orgao = roms_dir.parent.name if roms_dir.parent.name in ("MinC", "MTur") else None
    if expected_orgao is None and roms_dir.name in ("MinC", "MTur"):
        expected_orgao = roms_dir.name
    summaries = []
    for summary_path in sorted(roms_dir.glob("*.json")):
        try:
            raw = json.loads(summary_path.read_text(encoding="utf-8"))
            summary = IndicatorSummary(**raw)
            if expected_orgao is not None and summary.orgao != expected_orgao:
                raise ValueError(
                    f"{summary_path}: orgao {summary.orgao!r} no sidecar diverge do diretório "
                    f"de origem {expected_orgao!r} — sidecar mal-rotulado/copiado"
                )
            summaries.append(summary)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise ValueError(f"sumário inválido em {summary_path}: {exc}") from exc
    return summaries


def _load_capa_fields(
    capa_path: Path, orgao: str, data_dir: Path
) -> tuple[dict[str, object], list[str]]:
    """Carrega e funde as capas CSV (comum + órgão) num único dict de campos.
    Capa ausente/comum vira rascunho (warnings), nunca falha técnica —
    processar não exige capa (ticket 02)."""
    warnings: list[str] = []
    campos: dict[str, object] = {}

    orgao_capa = data_dir / f"capa_{orgao}.csv"
    for label, path in (("comum", capa_path), ("de " + orgao, orgao_capa)):
        if not path.exists():
            warnings.append(f"capa {label} não encontrada em {path} — campos a preencher")
            continue
        try:
            campos.update(read_capa_csv_fields(path))
        except (OSError, ValueError) as exc:
            warnings.append(f"falha ao ler capa {label} ({path}): {exc} — campos a preencher")
    return campos, warnings


def _read_valor_base(data_dir: Path, warnings: list[str]) -> float | None:
    """Valor mensal a partir de `objetos.csv`. Ausente → `None` (glosa não
    calculada, ticket 01); malformado → `ValueError` (falha técnica, Q5)."""
    path = data_dir / OBJETOS_FILENAME
    try:
        objetos = read_objetos(path)
    except FileNotFoundError:
        warnings.append(f"objetos.csv não encontrado em {data_dir} — glosa não calculada")
        return None
    except ValueError as exc:
        raise ValueError(f"objetos.csv malformado em {path}: {exc}") from exc
    warnings.extend(objetos.warnings)
    return objetos.total_mensal


def run_report(
    competencia: str,
    capa_path: Path,
    roms_dir: Path,
    output_path: Path,
    config_dir: Path,
    *,
    expected_orgao: str | None = None,
    is_final_month: bool = False,
    data_dir: Path | None = None,
) -> ReportResult:
    orgao = expected_orgao or ""
    data_dir = data_dir or capa_path.parent

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
    dependency_check = check_report_ready(
        competencia, orgao, capa_path, roms_dir, data_dir=data_dir
    )
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
    capa_fields, capa_caveat = _load_capa_fields(capa_path, orgao, data_dir)
    warnings.extend(capa_caveat)
    warnings.extend(validate_periodo_competencia(capa_fields, competencia))
    warnings_gerais: list[str] = []

    try:
        valor_base = _read_valor_base(data_dir, warnings_gerais)
        warnings.extend(warnings_gerais)
    except ValueError as exc:
        return _error(str(exc))  # Q5: malformado é FALHA (exit 1)
    except OSError as exc:
        return _error(f"falha ao ler objetos (metric source) em {data_dir}: {exc}")
    for warning in warnings:
        logger.warning(warning)
    if valor_base is None:
        log_event(
            "glosa_nao_calculada",
            "glosa monetária não calculada",
            "WARNING",
            orgao=orgao,
            motivo="valor mensal ausente em objetos.csv",
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
        return _error(f"falha ao escrever {output_path}: {exc} — {WRITE_FAILURE_HINT}")
    except Exception as exc:  # border: never leak a raw traceback past the CLI
        return _error(f"falha inesperada ao montar {output_path}: {exc}")

    try:
        glosa = compute_report_glosa(
            competencia, summaries, valor_base, is_final_month=is_final_month, historico=historico
        )
    except Exception as exc:  # border: never leak a raw traceback past the CLI
        return _error(f"falha inesperada ao calcular glosa de {competencia}: {exc}")
    historico[competencia] = historico_entry(competencia, glosa)
    try:
        write_historico(historico_path, historico)
    except OSError as exc:
        warning = (
            f"falha ao gravar histórico de glosa em {historico_path}: {exc} — {WRITE_FAILURE_HINT}"
        )
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