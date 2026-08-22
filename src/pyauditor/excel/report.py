"""Build the consolidated Excel report from measured indicator summaries.

The generated workbook may contain the following worksheets, in order:

1. ``CAPA_E_CONTROLE``, when cover fields are supplied;
2. ``CADASTROS``, when indicator configurations are supplied;
3. ``INMS_BASE``;
4. the operational group worksheets declared by ``GROUP_TABS``;
5. ``GLOSAS``;
6. ``EVIDENCIAS``, when indicator configurations are supplied.

Indicator summaries are produced by ``measure`` and stored alongside each ROM.
The cover fields originate from the workbook created by ``bootstrap``.

Workbook construction is performed entirely in memory. Persistence is handled
separately by :func:`build_report`, which writes the completed workbook
atomically and closes it deterministically.

Columns intended for manual completion by contract inspectors remain blank.
The report does not infer or fabricate fiscal evidence, SEI references,
justifications, applicability decisions, or other manual declarations.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Final

from openpyxl import Workbook
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.worksheet import Worksheet

from pyauditor.atomic_write import atomic_write
from pyauditor.codes import contractual_sort_key, format_inms_code
from pyauditor.config.models import IndicatorConfig
from pyauditor.excel._style import CellValue
from pyauditor.excel._style import new_sheet as _new_sheet
from pyauditor.excel._style import write_row as _write_row
from pyauditor.excel.capa import SHEET_NAME as CAPA_SHEET_NAME
from pyauditor.excel.capa import render_capa_sheet
from pyauditor.excel.glosas import (
    GlosaResult,
    Historico,
    compute_glosa,
    houve_reincidencia,
    saldo_anterior_pct_de,
)
from pyauditor.excel.groups import GROUP_TABS, group_for_summary
from pyauditor.excel.inms_base import inms_base_fields
from pyauditor.rom.dedup import deduplicate_summaries
from pyauditor.rom.summary import IndicatorSummary

__all__: Final[tuple[str, ...]] = (
    'CADASTROS_SHEET',
    'EVIDENCIAS_SHEET',
    'GLOSAS_SHEET',
    'INMS_BASE_SHEET',
    'build_report',
    'build_report_workbook',
    'compute_report_glosa',
)

CADASTROS_SHEET: Final[str] = 'CADASTROS'
EVIDENCIAS_SHEET: Final[str] = 'EVIDENCIAS'
INMS_BASE_SHEET: Final[str] = 'INMS_BASE'
GLOSAS_SHEET: Final[str] = 'GLOSAS'

_INMS_BASE_COLUMNS: Final[tuple[str, ...]] = (
    'Competência',
    'Item contratual',
    'Serviço',
    'Grupo operacional',
    'Código INMS',
    'Descrição',
    'Órgão',
    'Meta mínima ou máxima',
    'Sentido da meta',
    'Numerador',
    'Denominador',
    'Resultado calculado',
    'Unidade',
    'Aplicabilidade',
    'Resultado esperado',
    'Conformidade',
    'Diferença para a meta',
    'Ocorrência de glosa',
    'Percentual de glosa',
    'Valor-base',
    'Valor da glosa',
    'Justificativa',
    'Referência da evidência',
    'Número SEI',
    'Responsável pela evidência',
    'Observação do fiscal',
)

_GROUP_TAB_COLUMNS: Final[tuple[str, ...]] = (
    'Código INMS',
    'Descrição',
    'Serviço',
    'Órgão',
    'Resultado (%)',
    'Meta',
    'Conformidade',
    'Penalidade (pontos)',
)

_GLOSAS_COLUMNS: Final[tuple[str, ...]] = (
    'Competência',
    'Σ Pontos_NMS do mês',
    'Saldo recebido do mês anterior (p.p.)',
    'Percentual de ajuste',
    'Valor-base',
    'Valor da glosa',
    'Teto atingido?',
    'Saldo rolado para o mês seguinte (p.p.)',
    'Reincidência (3x/6m)?',
)

_CADASTROS_COLUMNS: Final[tuple[str, ...]] = (
    'Código INMS',
    'Descrição',
    'Formato',
    'Meta',
    'Sentido',
    'Penalidade (pontos base)',
    'Penalidade (p.p. por descumprimento)',
)

_EVIDENCIAS_COLUMNS: Final[tuple[str, ...]] = (
    'Competência',
    'Código INMS',
    'Tipo de evidência',
    'Descrição',
    'Fonte/URL',
    'Responsável pela coleta',
    'Data de coleta',
    'Status',
)

_EVIDENCIAS_TIPOS: Final[tuple[str, ...]] = (
    'Planilha original',
    'Print de sistema',
    'Documento SEI',
    'E-mail de confirmação',
    'Relatório de monitoramento',
    'Foto/registro visual',
    'Outro',
)

_EVIDENCIAS_STATUS: Final[tuple[str, ...]] = (
    'Pendente',
    'Coletada',
    'Validada',
)

_MINIMUM_BODY_ROW: Final[int] = 2


def _sort_key(
    summary: IndicatorSummary,
) -> tuple[tuple[int, str, int, str], str]:
    """Return a deterministic contractual and asset ordering key."""
    return (
        contractual_sort_key(summary.contractual_id),
        summary.asset or '',
    )


def _config_sort_key(
    config: IndicatorConfig,
) -> tuple[int, str, int, str]:
    """Return the contractual ordering key for an indicator configuration."""
    return contractual_sort_key(config.indicator.contractual_id)


def _cadastros_row(
    config: IndicatorConfig,
) -> tuple[CellValue, ...]:
    """Convert an indicator configuration into a CADASTROS worksheet row."""
    target = config.target
    penalty = config.penalty

    return (
        format_inms_code(config.indicator.contractual_id),
        config.indicator.name,
        config.calculation.shape,
        target.value if target is not None else None,
        target.operator if target is not None else None,
        penalty.base_points if penalty is not None else None,
        penalty.step_points if penalty is not None else None,
    )


def _evidencias_row(
    competencia: str,
    config: IndicatorConfig,
) -> tuple[CellValue, ...]:
    """Create an evidence row prepared for manual fiscal completion."""
    return (
        competencia,
        format_inms_code(config.indicator.contractual_id),
        None,
        None,
        None,
        None,
        None,
        'Pendente',
    )


def _inline_validation_formula(values: tuple[str, ...]) -> str:
    """Build a safe inline Excel list-validation formula.

    Inline validation values cannot contain commas or double quotes because
    Excel interprets those characters as list or formula delimiters.

    Args:
        values: Controlled values exposed by the validation list.

    Returns:
        An Excel formula containing the comma-separated validation values.

    Raises:
        ValueError: If the list is empty, contains unsupported characters, or
            exceeds Excel's 255-character inline validation limit.
    """
    if not values:
        raise ValueError('Data-validation values must not be empty.')

    if any(',' in value or '"' in value for value in values):
        raise ValueError(
            'Inline data-validation values must not contain commas or quotes.'
        )

    formula = f'"{",".join(values)}"'
    if len(formula) > 255:
        raise ValueError(
            "Inline data-validation formula exceeds Excel's 255-characterlimit."
        )

    return formula


def _add_evidencias_validations(
    sheet: Worksheet,
    last_row: int,
) -> None:
    """Apply controlled-value validation to populated evidence rows."""
    if last_row < _MINIMUM_BODY_ROW:
        return

    tipo_validation = DataValidation(
        type='list',
        formula1=_inline_validation_formula(_EVIDENCIAS_TIPOS),
        allow_blank=True,
        errorStyle='stop',
        errorTitle='Tipo de evidência inválido',
        error='Selecione um tipo de evidência disponível na lista.',
        showErrorMessage=True,
    )
    sheet.add_data_validation(tipo_validation)
    tipo_validation.add(f'C{_MINIMUM_BODY_ROW}:C{last_row}')

    status_validation = DataValidation(
        type='list',
        formula1=_inline_validation_formula(_EVIDENCIAS_STATUS),
        allow_blank=False,
        errorStyle='stop',
        errorTitle='Status inválido',
        error='Selecione um status disponível na lista.',
        showErrorMessage=True,
    )
    sheet.add_data_validation(status_validation)
    status_validation.add(f'H{_MINIMUM_BODY_ROW}:H{last_row}')


def _build_cadastros_sheet(
    workbook: Workbook,
    configs: Sequence[IndicatorConfig],
) -> None:
    """Create CADASTROS, including an empty schema when no configs exist."""
    sheet = _new_sheet(
        workbook,
        CADASTROS_SHEET,
        _CADASTROS_COLUMNS,
        width=28,
    )

    for row_index, config in enumerate(
        sorted(configs, key=_config_sort_key),
        start=_MINIMUM_BODY_ROW,
    ):
        _write_row(sheet, row_index, _cadastros_row(config))


def _build_evidencias_sheet(
    workbook: Workbook,
    competencia: str,
    configs: Sequence[IndicatorConfig],
) -> None:
    """Create EVIDENCIAS and its controlled-value validations."""
    sheet = _new_sheet(
        workbook,
        EVIDENCIAS_SHEET,
        _EVIDENCIAS_COLUMNS,
        width=24,
    )
    sorted_configs = sorted(configs, key=_config_sort_key)

    for row_index, config in enumerate(
        sorted_configs,
        start=_MINIMUM_BODY_ROW,
    ):
        _write_row(
            sheet,
            row_index,
            _evidencias_row(competencia, config),
        )

    last_row = len(sorted_configs) + 1
    _add_evidencias_validations(sheet, last_row)


def _inms_base_row(
    competencia: str,
    summary: IndicatorSummary,
) -> tuple[CellValue, ...]:
    """Convert a measured summary into an INMS_BASE worksheet row."""
    group = group_for_summary(
        summary.indicator_id,
        summary.contractual_id,
    )
    row = inms_base_fields(summary, competencia, grupo_operacional=group)

    return (
        row.competencia,
        None,
        row.servico,
        row.grupo_operacional,
        row.codigo_inms,
        row.descricao,
        row.orgao,
        row.meta,
        row.sentido,
        row.numerador,
        row.denominador,
        row.resultado,
        row.unidade,
        None,
        None,
        row.conformidade,
        row.diferenca,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
    )


def _group_row(
    summary: IndicatorSummary,
) -> tuple[CellValue, ...]:
    """Convert a measured summary into an operational group row."""
    return (
        format_inms_code(summary.contractual_id),
        summary.name,
        summary.asset,
        summary.orgao,
        round(summary.result_pct, 2),
        summary.target_value,
        'Conforme' if summary.conforms else 'Não conforme',
        round(summary.penalty_points, 2),
    )


def _summaries_for_glosa(
    summaries: Sequence[IndicatorSummary],
) -> list[IndicatorSummary]:
    """Select summaries that contribute to the monthly glosa (dedup
    compartilhado — ``rom.dedup.deduplicate_summaries``, ticket 07)."""
    return deduplicate_summaries(summaries)


def compute_report_glosa(
    competencia: str,
    summaries: Sequence[IndicatorSummary],
    valor_base: float | None,
    *,
    is_final_month: bool = False,
    historico: Historico | None = None,
) -> GlosaResult:
    """Compute the monthly glosa rendered by the report.

    Base summaries are excluded when category-derived summaries exist for the
    same contractual indicator and asset. The derived category penalties are
    then summed exactly once.

    Historical state supplies the percentage-point balance rolled over from
    the previous reporting period. Reincidence is not part of the returned
    calculation because it is a reporting flag evaluated separately.

    Args:
        competencia: Reporting period used to resolve historical rollover.
        summaries: Measured indicator summaries for one organization.
        valor_base: Monetary base used to calculate the glosa, when available.
        is_final_month: Whether rollover must follow final-month rules.
        historico: Previously persisted glosa history. Missing history is
            treated as empty.

    Returns:
        The calculated monthly glosa and rollover state.

    Raises:
        ValueError: Propagates invalid financial inputs or reporting periods
            rejected by the glosa domain functions.
    """
    effective_history = historico if historico is not None else {}
    selected_summaries = _summaries_for_glosa(summaries)
    total_points = sum(summary.penalty_points for summary in selected_summaries)
    previous_balance = saldo_anterior_pct_de(
        effective_history,
        competencia,
    )

    return compute_glosa(
        total_points,
        valor_base,
        is_final_month=is_final_month,
        saldo_anterior_pct=previous_balance,
    )


def _build_inms_base_sheet(
    workbook: Workbook,
    competencia: str,
    summaries: Sequence[IndicatorSummary],
) -> None:
    """Create and populate the canonical INMS_BASE worksheet."""
    sheet = _new_sheet(
        workbook,
        INMS_BASE_SHEET,
        _INMS_BASE_COLUMNS,
        width=20,
    )

    for row_index, summary in enumerate(
        sorted(summaries, key=_sort_key),
        start=_MINIMUM_BODY_ROW,
    ):
        _write_row(
            sheet,
            row_index,
            _inms_base_row(competencia, summary),
        )


def _build_group_sheets(
    workbook: Workbook,
    summaries: Sequence[IndicatorSummary],
) -> None:
    """Create every configured operational group worksheet."""
    summaries_by_group: dict[str, list[IndicatorSummary]] = {
        group: [] for group in GROUP_TABS
    }

    for summary in summaries:
        group = group_for_summary(
            summary.indicator_id,
            summary.contractual_id,
        )
        if group is not None:
            summaries_by_group[group].append(summary)

    for group in GROUP_TABS:
        sheet = _new_sheet(
            workbook,
            group,
            _GROUP_TAB_COLUMNS,
            width=22,
        )

        for row_index, summary in enumerate(
            sorted(summaries_by_group[group], key=_sort_key),
            start=_MINIMUM_BODY_ROW,
        ):
            _write_row(
                sheet,
                row_index,
                _group_row(summary),
            )


def _build_glosas_sheet(
    workbook: Workbook,
    competencia: str,
    summaries: Sequence[IndicatorSummary],
    valor_base: float | None,
    *,
    is_final_month: bool,
    historico: Historico,
) -> None:
    """Create the monthly financial adjustment worksheet."""
    sheet = _new_sheet(
        workbook,
        GLOSAS_SHEET,
        _GLOSAS_COLUMNS,
        width=26,
    )

    previous_balance = saldo_anterior_pct_de(
        historico,
        competencia,
    )
    glosa = compute_report_glosa(
        competencia,
        summaries,
        valor_base,
        is_final_month=is_final_month,
        historico=historico,
    )
    reincidencia = houve_reincidencia(
        historico,
        competencia,
        glosa.teto_atingido,
    )

    _write_row(
        sheet,
        _MINIMUM_BODY_ROW,
        (
            competencia,
            round(glosa.total_points, 2),
            round(previous_balance, 5) if previous_balance else None,
            round(glosa.percentual_ajuste, 5),
            glosa.valor_base,
            (
                round(glosa.valor_da_glosa, 2)
                if glosa.valor_da_glosa is not None
                else None
            ),
            'S' if glosa.teto_atingido else 'N',
            (
                round(glosa.saldo_rolado_pct, 5)
                if glosa.saldo_rolado_pct
                else None
            ),
            'S' if reincidencia else 'N',
        ),
    )


def build_report_workbook(
    competencia: str,
    summaries: Sequence[IndicatorSummary],
    valor_base: float | None = None,
    *,
    is_final_month: bool = False,
    capa_fields: dict[str, object] | None = None,
    configs: Sequence[IndicatorConfig] | None = None,
    historico: Historico | None = None,
) -> Workbook:
    """Build the consolidated report workbook entirely in memory.

    The cover worksheet is created first when ``capa_fields`` is supplied.
    ``CADASTROS`` and ``EVIDENCIAS`` are created when ``configs`` is supplied,
    including when it is an empty sequence. An empty configuration sequence
    therefore produces both worksheet schemas without data rows.

    ``INMS_BASE``, every group worksheet, and ``GLOSAS`` are always created.

    The caller owns the returned workbook and must close it. If construction
    fails, this function closes the partially built workbook before propagating
    the original exception.

    Args:
        competencia: Reporting period displayed in report rows and used for
            historical glosa lookup.
        summaries: Measured indicator summaries for one organization.
        valor_base: Monetary base used for the monthly glosa.
        is_final_month: Whether the reporting period follows final-month
            rollover rules.
        capa_fields: Cover worksheet fields. When omitted, the cover worksheet
            is not created.
        configs: Indicator configurations used by CADASTROS and EVIDENCIAS.
            When omitted, both worksheets are skipped.
        historico: Previously persisted glosa history. Missing history is
            treated as empty.

    Returns:
        An open, fully constructed workbook owned by the caller.

    Raises:
        ValueError: If report values violate worksheet or financial contracts.
        Exception: Propagates errors raised while rendering worksheets or
            calculating the report.
    """
    workbook = Workbook()

    try:
        default_sheet = workbook.worksheets[0]
        workbook.remove(default_sheet)

        if capa_fields is not None:
            cover_sheet = workbook.create_sheet(
                title=CAPA_SHEET_NAME,
                index=0,
            )
            render_capa_sheet(cover_sheet, capa_fields)

        if configs is not None:
            _build_cadastros_sheet(workbook, configs)

        _build_inms_base_sheet(
            workbook,
            competencia,
            summaries,
        )
        _build_group_sheets(
            workbook,
            summaries,
        )

        effective_history = historico if historico is not None else {}
        _build_glosas_sheet(
            workbook,
            competencia,
            summaries,
            valor_base,
            is_final_month=is_final_month,
            historico=effective_history,
        )

        if configs is not None:
            _build_evidencias_sheet(
                workbook,
                competencia,
                configs,
            )

        return workbook
    except BaseException:
        workbook.close()
        raise


def build_report(
    competencia: str,
    summaries: Sequence[IndicatorSummary],
    output_path: Path,
    valor_base: float | None = None,
    *,
    is_final_month: bool = False,
    capa_fields: dict[str, object] | None = None,
    configs: Sequence[IndicatorConfig] | None = None,
    historico: Historico | None = None,
) -> None:
    """Build and atomically persist the consolidated Excel report.

    The output file is replaced only after the complete workbook has been
    successfully written through the atomic-write mechanism. The in-memory
    workbook is closed whether persistence succeeds or fails.

    Args:
        competencia: Reporting period displayed in the report.
        summaries: Measured indicator summaries for one organization.
        output_path: Destination path for the generated XLSX file.
        valor_base: Monetary base used for the monthly glosa.
        is_final_month: Whether final-month rollover rules apply.
        capa_fields: Optional fields for the cover worksheet.
        configs: Optional indicator configurations for CADASTROS and
            EVIDENCIAS.
        historico: Optional previously persisted glosa history.

    Raises:
        OSError: If the destination cannot be written or replaced.
        ValueError: If report data violates worksheet or financial contracts.
        Exception: Propagates workbook-rendering and serialization errors.
    """
    workbook = build_report_workbook(
        competencia,
        summaries,
        valor_base,
        is_final_month=is_final_month,
        capa_fields=capa_fields,
        configs=configs,
        historico=historico,
    )

    try:
        atomic_write(output_path, workbook.save)
    finally:
        workbook.close()
