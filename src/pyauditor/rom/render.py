"""Generic ROM Markdown template + per-shape memória de cálculo renderers.

Fixed sections (identificação, linhas aprovadas, rejeições, resultado vs
meta, responsáveis) are the same for every shape; only the memória de
cálculo — and the "ressalva interpretativa" (only shown for indicators with a
step-based `penalty`) — varies. See .scratch/melhoria_rom/map.md for the spec
this template implements.
"""

import math
from collections.abc import Callable
from typing import Any

from pyauditor.codes import format_inms_code
from pyauditor.config.models import IndicatorConfig
from pyauditor.engine.pipeline import MeasurementProvenance, MeasurementResult
from pyauditor.engine.quality_gates import QualityGateReport
from pyauditor.engine.strategies._target import shortfall
from pyauditor.engine.strategies.base import CalculationResult

_CAPA_PLACEHOLDER = "[a preencher]"


def _require_list(value: object, *, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise TypeError(f"memoria[{field!r}] deveria ser list, veio {type(value).__name__}")
    return value


def _md_cell(value: object) -> str:
    """Escape a value before it lands in a Markdown table cell — a stray
    `|` or embedded newline from CSV-derived data would otherwise silently
    shift the table's column alignment in what's meant to be a formal,
    auditable record."""
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_ratio_memoria(calculation: CalculationResult) -> str:
    numerator = calculation.memoria["numerator"]
    denominator = calculation.memoria["denominator"]
    return (
        f"- Numerador: {numerator}\n- Denominador: {denominator}\n"
        f"- Resultado: {calculation.result_pct:.2f}%"
    )


def render_segmented_ratio_memoria(calculation: CalculationResult) -> str:
    categories = _require_list(calculation.memoria["categories"], field="categories")
    lines = [
        f"| {_md_cell(c['name'])} | {c['numerator']} | {c['denominator']} | "
        f"{c['result_pct']:.2f}% | {c['penalty_points']:.2f} |"
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
    return f"- QRC (recomendados): {qrc}\n- QCSI (implantados): {qcsi}\n- CNI = QRC - QCSI = {cni}"


def render_external_catalog_sum_memoria(calculation: CalculationResult) -> str:
    occurrences = _require_list(calculation.memoria["occurrences"], field="occurrences")
    if not occurrences:
        rows_markdown = "| — | — | nenhuma ocorrência | — |"
    else:
        rows_markdown = "\n".join(
            f"| {_md_cell(o['occurrence_id'])} | {_md_cell(o['catalog_id'])} | "
            f"{_md_cell(o['descricao'])} | {o['pontos']} |"
            for o in occurrences
        )
    return (
        "| Ocorrência | Item Anexo E | Descrição | Pontos |\n"
        "|---|---|---|---|\n"
        f"{rows_markdown}\n\n"
        f"- Σ Pontos_NMS = {calculation.memoria['total_points']}"
    )


def render_precomputed_table_memoria(calculation: CalculationResult) -> str:
    categories = _require_list(calculation.memoria["categories"], field="categories")
    if not categories:
        rows_markdown = "| — | — | nenhuma linha |"
    else:
        rows_markdown = "\n".join(
            f"| {_md_cell(c['name'])} | {c['result_pct']:.2f}% | {c['penalty_points']:.2f} |"
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


def _capa_value(capa_fields: dict[str, object], label: str) -> str:
    value = capa_fields.get(label)
    if value in (None, ""):
        return _CAPA_PLACEHOLDER
    # Free-text capa field — strip embedded newlines so it can't fake a
    # heading/bullet in the rendered Markdown.
    return str(value).replace("\n", " ")


def _render_identificacao(
    config: IndicatorConfig,
    provenance: MeasurementProvenance,
    capa_fields: dict[str, object],
    h: str = "##",
) -> str:
    periodo_inicial = _capa_value(capa_fields, "Período inicial da aferição")
    periodo_final = _capa_value(capa_fields, "Período final da aferição")
    return (
        f"{h} Identificação\n"
        f"- Contrato: {config.scope.contract}\n"
        f"- Órgão: {config.scope.orgao}\n"
        f"- Competência: {_capa_value(capa_fields, 'Competência')}\n"
        f"- Período da aferição: {periodo_inicial} a {periodo_final}\n"
        f"- Data de processamento: {provenance.processed_at.isoformat(timespec='seconds')}\n"
        f"- Versão do pipeline: {provenance.pipeline_version}\n"
        f"- Versão da configuração: {provenance.config_hash or '[indisponível]'}\n"
        f"- Arquivo de origem: {provenance.csv_path.name} "
        f"(SHA-256: {provenance.csv_hash}, delimitador `{provenance.delimiter}`, "
        f"codificação {provenance.encoding})"
    )


def _render_responsaveis(capa_fields: dict[str, object], h: str = "##") -> str:
    return (
        f"{h} Responsáveis\n"
        f"- Fiscal técnico: {_capa_value(capa_fields, 'Fiscal técnico')}\n"
        f"- Fiscal requisitante: {_capa_value(capa_fields, 'Fiscal requisitante')}\n"
        f"- Fiscal administrativo: {_capa_value(capa_fields, 'Fiscal administrativo')}\n"
        f"- Gestor do contrato: {_capa_value(capa_fields, 'Gestor do contrato')}"
    )


def _render_ressalva_interpretativa(
    config: IndicatorConfig, calculation: CalculationResult
) -> str | None:
    """Only shapes with a step-based `penalty` (today: `ratio`) have a
    linear-vs-degraus ambiguity to disclose, and only when there's an actual
    shortfall to score — a conforming indicator has nothing to interpret."""
    if config.penalty is None or calculation.penalty_points <= 0:
        return None
    assert config.target is not None  # `penalty` always accompanies `target` for `ratio`

    deficit = max(
        shortfall(calculation.result_pct, config.target.operator, config.target.value), 0.0
    )
    steps = deficit / config.penalty.step_size_pct
    base = config.penalty.base_points
    step_points = config.penalty.step_points
    linear_points = calculation.penalty_points
    floor_points = base + math.floor(steps) * step_points
    ceil_points = base + math.ceil(steps) * step_points

    formula_linear = "base + (déficit / passo) x pontos_degrau"
    formula_floor = "base + ⌊déficit / passo⌋ x pontos_degrau"
    formula_ceil = "base + ⌈déficit / passo⌉ x pontos_degrau"
    return (
        "| Leitura | Fórmula | Pontuação apurada |\n"
        "|---|---|---|\n"
        f"| Linear contínua (adotada) | {formula_linear} | {linear_points:.2f} |\n"
        f"| Degraus completos | {formula_floor} | {floor_points:.2f} |\n"
        f"| Qualquer fração inicia novo degrau | {formula_ceil} | {ceil_points:.2f} |\n"
        "\n"
        "> A leitura linear contínua é a metodologia adotada por este pipeline. As\n"
        "> demais leituras são apresentadas para transparência e não foram validadas\n"
        "> formalmente pela gestão contratual/assessoria jurídica."
    )


def _render_linhas_aprovadas(gate_report: QualityGateReport, h: str = "##") -> str:
    return (
        f"{h} Linhas aprovadas pelo quality gate\n"
        f"- Linhas lidas: {len(gate_report.accepted) + len(gate_report.rejected)}\n"
        f"- Linhas aprovadas: {len(gate_report.accepted)}\n\n"
        "> Aprovação pelo quality gate não equivale à população contratual completa\n"
        "> (registros podem ser rejeitados por critérios estruturais que não decidem\n"
        "> se pertencem ao universo do indicador)."
    )


def _render_resultado_vs_meta(
    config: IndicatorConfig, calculation: CalculationResult, h: str = "##"
) -> str:
    conformidade = "conforme" if calculation.conforms else "não conforme"
    if config.target is not None:
        resultado_vs_meta = (
            f"- Meta: {config.target.operator} {config.target.value}%\n"
            f"- Resultado: {calculation.result_pct:.2f}% — **{conformidade}**"
        )
    else:
        # `external_catalog_sum`: Anexo E is a linear point sum, no percentage meta.
        resultado_vs_meta = (
            f"- Meta: não aplicável (soma de pontos, ver Anexo E) — **{conformidade}**"
        )

    return (
        f"{h} Resultado vs meta\n{resultado_vs_meta}\n"
        f"- Pontuação apurada: {calculation.penalty_points:.2f} pontos\n\n"
        '> "Pontuação apurada" não implica sanção administrativa — ver processo\n'
        "> sancionador próprio, se cabível."
    )


def _org_body(
    result: MeasurementResult, capa_fields: dict[str, object], h: str = "##"
) -> list[str]:
    """The per-orgão body sections of a ROM — shared by the standalone
    `render_rom` (h=`##`) and the combined `render_combined_rom` (nested
    under each orgão heading, h=`###`)."""
    config = result.config
    gate_report = result.quality_gate_report
    calculation = result.calculation
    provenance = result.provenance

    rejected_table = "\n".join(
        f"| {_md_cell(row.row_id)} | {_md_cell(row.reason)} |" for row in gate_report.rejected
    ) or "| — | nenhuna rejeição |"

    memoria_renderer = _MEMORIA_RENDERERS[config.calculation.shape]

    sections = [
        _render_identificacao(config, provenance, capa_fields, h),
        _render_linhas_aprovadas(gate_report, h),
        f"{h} Rejeições\n| ID | Motivo |\n|---|---|\n{rejected_table}",
        f"{h} Memória de cálculo\n{memoria_renderer(calculation)}",
    ]

    ressalva = _render_ressalva_interpretativa(config, calculation)
    if ressalva is not None:
        sections.append(f"{h} Ressalva interpretativa\n{ressalva}")

    sections.append(_render_resultado_vs_meta(config, calculation, h))
    sections.append(_render_responsaveis(capa_fields, h))
    sections.append(
        "---\n"
        "*Competência, período e responsáveis refletem o estado da capa no momento "
        "em que este ROM foi gerado — não são valores definitivos.*"
    )

    return sections


def render_rom(result: MeasurementResult, capa_fields: dict[str, object] | None = None) -> str:
    capa_fields = capa_fields or {}
    config = result.config

    titulo = format_inms_code(config.indicator.contractual_id)
    if config.indicator.asset is not None:
        titulo += f" — {config.indicator.asset}"

    return (
        "\n\n".join(
            [f"# ROM — {titulo} ({config.indicator.name})", *_org_body(result, capa_fields, "##")]
        )
        + "\n"
    )


def render_combined_rom(
    result_a: MeasurementResult,
    result_b: MeasurementResult,
    capa_by_orgao: dict[str, dict[str, object]] | None = None,
) -> str:
    """One markdown per indicator covering both orgãos: the full ROM body of
    each, stacked under a `## <órgão>` heading. Written when `measure` runs
    with `--orgao both`, alongside the per-orgão ROMs."""
    capa_by_orgao = capa_by_orgao or {}
    config_a = result_a.config
    config_b = result_b.config
    org_a = config_a.scope.orgao
    org_b = config_b.scope.orgao
    capa_a = capa_by_orgao.get(org_a, {})
    capa_b = capa_by_orgao.get(org_b, {})

    titulo = format_inms_code(config_a.indicator.contractual_id)
    if config_a.indicator.asset is not None:
        titulo += f" — {config_a.indicator.asset}"

    sections = [
        f"# ROM — {titulo} ({config_a.indicator.name}) — {org_a} e {org_b}",
        f"## {org_a}",
        *_org_body(result_a, capa_a, "###"),
        f"## {org_b}",
        *_org_body(result_b, capa_b, "###"),
    ]

    return "\n\n".join(sections) + "\n"
