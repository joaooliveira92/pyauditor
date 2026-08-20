"""`pyauditor report <competência>` — consolidate the ROMs `measure` wrote
into the final Excel: `CADASTROS` + `INMS_BASE` + per-group tabs + `GLOSAS`
(spec §6/§13).
"""

import json
from pathlib import Path

from pyauditor.engine.pipeline import discover_configs
from pyauditor.excel.capa import read_capa_fields
from pyauditor.excel.glosas import historico_entry, read_historico, write_historico
from pyauditor.excel.report import build_report, compute_report_glosa
from pyauditor.logging import logger
from pyauditor.rom.summary import IndicatorSummary

HISTORICO_FILENAME = "glosa_historico.json"


def _load_summaries(roms_dir: Path) -> list[IndicatorSummary]:
    summaries = []
    for summary_path in sorted(roms_dir.glob("*.json")):
        raw = json.loads(summary_path.read_text(encoding="utf-8"))
        summaries.append(IndicatorSummary(**raw))
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
) -> int:
    if not capa_path.exists():
        logger.error(f"capa não encontrada em {capa_path} — rode `pyauditor bootstrap` primeiro")
        return 1

    competencia_dir = roms_dir / competencia
    if not competencia_dir.is_dir():
        logger.error(f"nenhum ROM encontrado em {competencia_dir} — rode `pyauditor measure` primeiro")
        return 1

    try:
        summaries = _load_summaries(competencia_dir)
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        logger.error(f"falha ao ler sumários de medição em {competencia_dir}: {exc}")
        return 1

    if not summaries:
        logger.error(f"nenhum sumário de medição (.json) encontrado em {competencia_dir}")
        return 1

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
        logger.warning(f"falha ao carregar configs de {config_dir}, CADASTROS será omitido: {exc}")
        configs = []

    historico_path = roms_dir / HISTORICO_FILENAME
    try:
        historico = read_historico(historico_path)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning(f"falha ao ler histórico de glosa em {historico_path}, rollover será 0: {exc}")
        historico = {}

    try:
        build_report(
            competencia, summaries, output_path, valor_base,
            is_final_month=is_final_month, capa_fields=capa_fields,
            configs=configs or None, historico=historico,
        )
    except OSError as exc:
        logger.error(f"falha ao escrever {output_path}: {exc}")
        return 1

    glosa = compute_report_glosa(
        competencia, summaries, valor_base, is_final_month=is_final_month, historico=historico
    )
    historico[competencia] = historico_entry(competencia, glosa)
    try:
        write_historico(historico_path, historico)
    except OSError as exc:
        logger.warning(f"falha ao gravar histórico de glosa em {historico_path}: {exc}")

    logger.info(f"relatório consolidado: {output_path} ({len(summaries)} indicadores)")
    return 0
