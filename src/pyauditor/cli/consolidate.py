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
from pathlib import Path

from pyauditor.excel.capa import read_capa_fields
from pyauditor.excel.consolidate import build_consolidated_workbook, read_existing_decisions
from pyauditor.logging import logger
from pyauditor.rom.summary import IndicatorSummary

_ORGAOS: tuple[str, str] = ("MinC", "MTur")


def _load_summaries(roms_dir: Path) -> list[IndicatorSummary]:
    summaries: list[IndicatorSummary] = []
    for summary_path in sorted(roms_dir.glob("*.json")):
        raw = json.loads(summary_path.read_text(encoding="utf-8"))
        summaries.append(IndicatorSummary(**raw))
    return summaries


def run_consolidate(
    competencia: str,
    report_dir: Path,
    roms_dir: Path,
    output_path: Path,
) -> int:
    report_paths = {orgao: report_dir / f"relatorio_{competencia}_{orgao}.xlsx" for orgao in _ORGAOS}
    missing = [str(path) for path in report_paths.values() if not path.exists()]
    if missing:
        logger.error(
            "faltam relatórios por órgão para consolidar: "
            + ", ".join(missing)
            + " — rode `pyauditor report` para cada órgão antes de `consolidate`"
        )
        return 1

    roms_dirs = {orgao: roms_dir / orgao / competencia for orgao in _ORGAOS}
    missing_roms = [str(d) for d in roms_dirs.values() if not d.is_dir()]
    if missing_roms:
        logger.error(
            "faltam ROMs por órgão para consolidar: " + ", ".join(missing_roms)
            + " — rode `pyauditor measure` para cada órgão antes de `consolidate`"
        )
        return 1

    try:
        minc = _load_summaries(roms_dirs["MinC"])
        mtur = _load_summaries(roms_dirs["MTur"])
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        logger.error(f"falha ao ler sumários de medição: {exc}")
        return 1

    if not minc or not mtur:
        logger.error("nenhum sumário de medição (.json) encontrado para um dos órgãos")
        return 1

    minc_capa = read_capa_fields(report_paths["MinC"])
    mtur_capa = read_capa_fields(report_paths["MTur"])

    existing_decisions = read_existing_decisions(output_path)
    if existing_decisions:
        logger.info(f"{len(existing_decisions)} decisão(ões) do fiscal preservada(s) de {output_path}")

    result = build_consolidated_workbook(
        competencia, minc, mtur, minc_capa, mtur_capa, existing_decisions
    )

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        result.workbook.save(output_path)
    except OSError as exc:
        logger.error(f"falha ao escrever {output_path}: {exc}")
        return 1

    logger.info(
        f"relatório consolidado: {output_path} "
        f"(total de pontos: {result.total_pontos:.2f}, glosa: {result.glosa_final:,.2f})"
    )
    return 0
