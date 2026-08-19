"""Generic ROM Markdown template + per-shape memória de cálculo renderers.

Fixed sections (cabeçalho, população, rejeições, resultado vs meta) are the
same for every shape (spec §7); only the memória de cálculo varies.
"""

from collections.abc import Callable

from pyauditor.engine.pipeline import MeasurementResult
from pyauditor.engine.strategies.base import CalculationResult


def render_ratio_memoria(calculation: CalculationResult) -> str:
    numerator = calculation.memoria["numerator"]
    denominator = calculation.memoria["denominator"]
    return f"- Numerador: {numerator}\n- Denominador: {denominator}\n- Resultado: {calculation.result_pct:.2f}%"


def render_segmented_ratio_memoria(calculation: CalculationResult) -> str:
    categories = calculation.memoria["categories"]
    assert isinstance(categories, list)
    lines = [
        f"| {c['name']} | {c['numerator']} | {c['denominator']} | {c['result_pct']:.2f}% | {c['penalty_points']:.2f} |"
        for c in categories
    ]
    table = "\n".join(lines)
    return (
        "| Categoria | Numerador | Denominador | Resultado | Penalidade |\n"
        "|---|---|---|---|---|\n"
        f"{table}\n\n"
        f"- Soma das penalidades: {calculation.penalty_points:.2f} pontos"
    )


def render_count_difference_memoria(calculation: CalculationResult) -> str:
    qrc = calculation.memoria["QRC"]
    qcsi = calculation.memoria["QCSI"]
    cni = calculation.memoria["CNI"]
    return f"- QRC (recomendados): {qrc}\n- QCSI (implantados): {qcsi}\n- CNI = QRC − QCSI = {cni}"


def render_external_catalog_sum_memoria(calculation: CalculationResult) -> str:
    occurrences = calculation.memoria["occurrences"]
    assert isinstance(occurrences, list)
    if not occurrences:
        rows_markdown = "| — | — | nenhuma ocorrência | — |"
    else:
        rows_markdown = "\n".join(
            f"| {o['occurrence_id']} | {o['catalog_id']} | {o['descricao']} | {o['pontos']} |"
            for o in occurrences
        )
    return (
        "| Ocorrência | Item Anexo E | Descrição | Pontos |\n"
        "|---|---|---|---|\n"
        f"{rows_markdown}\n\n"
        f"- Σ Pontos_NMS = {calculation.memoria['total_points']}"
    )


def render_precomputed_table_memoria(calculation: CalculationResult) -> str:
    categories = calculation.memoria["categories"]
    assert isinstance(categories, list)
    if not categories:
        rows_markdown = "| — | — | nenhuma linha |"
    else:
        rows_markdown = "\n".join(
            f"| {c['name']} | {c['result_pct']:.2f}% | {c['penalty_points']:.2f} |"
            for c in categories
        )
    return (
        "| Ativo | Resultado | Penalidade |\n"
        "|---|---|---|\n"
        f"{rows_markdown}\n\n"
        f"- Soma das penalidades: {calculation.penalty_points:.2f} pontos"
    )


_MEMORIA_RENDERERS: dict[str, Callable[[CalculationResult], str]] = {
    "ratio": render_ratio_memoria,
    "segmented_ratio": render_segmented_ratio_memoria,
    "count_difference": render_count_difference_memoria,
    "external_catalog_sum": render_external_catalog_sum_memoria,
    "precomputed_table": render_precomputed_table_memoria,
}


def render_rom(result: MeasurementResult) -> str:
    config = result.config
    gate_report = result.quality_gate_report
    calculation = result.calculation

    rejected_table = "\n".join(
        f"| {row.row_id} | {row.reason} |" for row in gate_report.rejected
    ) or "| — | nenhuma rejeição |"

    memoria_renderer = _MEMORIA_RENDERERS[config.calculation.shape]
    conformidade = "conforme" if calculation.conforms else "não conforme"

    if config.target is not None:
        resultado_vs_meta = (
            f"- Meta: {config.target.operator} {config.target.value}%\n"
            f"- Resultado: {calculation.result_pct:.2f}% — **{conformidade}**"
        )
    else:
        # `external_catalog_sum`: Anexo E is a linear point sum, no percentage meta.
        resultado_vs_meta = f"- Meta: não aplicável (soma de pontos, ver Anexo E) — **{conformidade}**"

    titulo = config.indicator.contractual_id
    if config.indicator.asset is not None:
        titulo += f" — {config.indicator.asset}"

    return f"""# ROM — {titulo} ({config.indicator.name})

**Contrato:** {config.scope.contract}
**Órgão:** {config.scope.orgao}

## População
- Linhas lidas: {len(gate_report.accepted) + len(gate_report.rejected)}
- Linhas aceitas: {len(gate_report.accepted)}

## Rejeições
| ID | Motivo |
|---|---|
{rejected_table}

## Memória de cálculo
{memoria_renderer(calculation)}

## Resultado vs meta
{resultado_vs_meta}
- Penalidade: {calculation.penalty_points:.2f} pontos
"""
