"""Dedup compartilhado de sumários derivados (ticket 07): `report`/
`consolidate` agrupam por `(contractual_id, asset)` e, quando categorias
derivadas existem no grupo, excluem a base para não contar o resultado dela
em duplicidade com as categorias — usado tanto para a glosa (`report.py`)
quanto para a aba `GLOSAS` do consolidado.

Fonte única: antes existiam duas cópias com nomes diferentes
(`_is_categoria_derived`+`_summaries_for_glosa` em `excel/report.py` vs
`_is_derived`+`_deduplicate` em `excel/consolidate.py`) e semânticas
divergentes — `_is_derived` testava `"." in indicator_id`, o que é sempre
verdadeiro para códigos INMS (`"1.7"` já contém um ponto), então nunca
excluía a base de fato. A checagem correta é o prefixo
`f"{contractual_id}."`.
"""

from collections.abc import Sequence

from pyauditor.rom.summary import IndicatorSummary


def is_categoria_derived(summary: IndicatorSummary) -> bool:
    """`indicator_id` é a base (`contractual_id`) seguida de um sufixo de
    categoria separado por ponto — não apenas conter um ponto, já que
    `contractual_id` (ex.: `"1.7"`) contém um por si só."""
    return summary.indicator_id.startswith(f"{summary.contractual_id}.")


def deduplicate_summaries(summaries: Sequence[IndicatorSummary]) -> list[IndicatorSummary]:
    """Agrupa por `(contractual_id, asset)`; quando o grupo tem categorias
    derivadas, mantém só as derivadas (a base fica implícita nelas).
    Grupos sem derivados passam inalterados."""
    grouped: dict[tuple[str, str | None], list[IndicatorSummary]] = {}
    for summary in summaries:
        grouped.setdefault((summary.contractual_id, summary.asset), []).append(summary)

    deduped: list[IndicatorSummary] = []
    for group in grouped.values():
        derived = [summary for summary in group if is_categoria_derived(summary)]
        deduped.extend(derived if derived else group)
    return deduped
