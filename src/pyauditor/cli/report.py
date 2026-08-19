"""`pyauditor report <competência>` — consolidate the ROMs `measure` wrote
into the final Excel: `INMS_BASE` + per-group tabs + `GLOSAS` (spec §6/§13).
"""

import json
from pathlib import Path

from pyauditor.excel.capa import read_valor_mensal_vigente
from pyauditor.excel.report import build_report
from pyauditor.logging import logger
from pyauditor.rom.summary import IndicatorSummary


def _load_summaries(roms_dir: Path) -> list[IndicatorSummary]:
    summaries = []
    for summary_path in sorted(roms_dir.glob("*.json")):
        raw = json.loads(summary_path.read_text(encoding="utf-8"))
        summaries.append(IndicatorSummary(**raw))
    return summaries


def run_report(competencia: str, capa_path: Path, roms_dir: Path, output_path: Path) -> int:
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

    valor_base = read_valor_mensal_vigente(capa_path)
    if valor_base is None:
        logger.info(
            "capa sem 'Valor mensal vigente' preenchido — GLOSAS terá percentual de ajuste "
            "mas não valor da glosa"
        )

    try:
        build_report(competencia, summaries, output_path, valor_base)
    except OSError as exc:
        logger.error(f"falha ao escrever {output_path}: {exc}")
        return 1

    logger.info(f"relatório consolidado: {output_path} ({len(summaries)} indicadores)")
    return 0
