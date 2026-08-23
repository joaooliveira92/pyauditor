"""Aba CADASTROS do relatório por órgão (ticket 09 SRP).

Builder e helpers de linha da planilha `CADASTROS`, extraídos de
`excel/report.py`.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from openpyxl import Workbook

from pyauditor.codes import format_inms_code
from pyauditor.config.models import IndicatorConfig
from pyauditor.excel._style import CellValue, new_sheet, write_row

CADASTROS_SHEET: Final[str] = 'CADASTROS'

_CADASTROS_COLUMNS: Final[tuple[str, ...]] = (
    'Código INMS',
    'Descrição',
    'Formato',
    'Meta',
    'Sentido',
    'Penalidade (pontos base)',
    'Penalidade (p.p. por descumprimento)',
)

_MINIMUM_BODY_ROW: Final[int] = 2


def _config_sort_key(
    config: IndicatorConfig,
) -> tuple[int, str, int, str]:
    """Return the contractual ordering key for an indicator configuration."""
    from pyauditor.codes import contractual_sort_key

    return contractual_sort_key(config.indicator.contractual_id)


def cadastros_row(
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


def build_cadastros_sheet(
    workbook: Workbook,
    configs: Sequence[IndicatorConfig],
) -> None:
    """Create CADASTROS, including an empty schema when no configs exist."""
    sheet = new_sheet(
        workbook,
        CADASTROS_SHEET,
        _CADASTROS_COLUMNS,
        width=28,
    )

    for row_index, config in enumerate(
        sorted(configs, key=_config_sort_key),
        start=_MINIMUM_BODY_ROW,
    ):
        write_row(sheet, row_index, cadastros_row(config))
