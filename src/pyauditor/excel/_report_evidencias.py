"""Aba EVIDENCIAS do relatório por órgão (ticket 09 SRP).

Builder, helpers de linha e validações de célula da planilha `EVIDENCIAS`,
extraídos de `excel/report.py`.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from openpyxl import Workbook
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.worksheet import Worksheet

from pyauditor.codes import format_inms_code
from pyauditor.config.models import IndicatorConfig
from pyauditor.excel._style import CellValue, new_sheet, write_row

EVIDENCIAS_SHEET: Final[str] = 'EVIDENCIAS'

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


def _inline_validation_formula(values: tuple[str, ...]) -> str:
    """Build a safe inline Excel list-validation formula.

    Inline validation values cannot contain commas or double quotes because
    Excel interprets those characters as list or formula delimiters.
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


def _config_sort_key(
    config: IndicatorConfig,
) -> tuple[int, str, int, str]:
    """Return the contractual ordering key for an indicator configuration."""
    from pyauditor.codes import contractual_sort_key

    return contractual_sort_key(config.indicator.contractual_id)


def evidencias_row(
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


def build_evidencias_sheet(
    workbook: Workbook,
    competencia: str,
    configs: Sequence[IndicatorConfig],
) -> None:
    """Create EVIDENCIAS and its controlled-value validations."""
    sheet = new_sheet(
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
        write_row(
            sheet,
            row_index,
            evidencias_row(competencia, config),
        )

    last_row = len(sorted_configs) + 1
    _add_evidencias_validations(sheet, last_row)
