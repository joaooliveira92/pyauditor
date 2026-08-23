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

Ticket 09 SRP: os builders por aba vivem em `excel/_report_cadastros.py`,
`_report_evidencias.py`, `_report_inms_base.py`, `_report_groups.py` e
`_report_glosas.py`; este módulo é o compositor e reexporta as constantes de
aba e a API pública preservada.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Final

from openpyxl import Workbook

from pyauditor.atomic_write import atomic_write
from pyauditor.config.models import IndicatorConfig
from pyauditor.excel._relatorio_glosa import compute_report_glosa
from pyauditor.excel._report_cadastros import (
    CADASTROS_SHEET,
    build_cadastros_sheet,
)
from pyauditor.excel._report_evidencias import (
    EVIDENCIAS_SHEET,
    build_evidencias_sheet,
)
from pyauditor.excel._report_glosas import (
    GLOSAS_SHEET,
    build_glosas_sheet,
)
from pyauditor.excel._report_groups import build_group_sheets
from pyauditor.excel._report_inms_base import (
    INMS_BASE_SHEET,
    build_inms_base_sheet,
)
from pyauditor.excel.capa import SHEET_NAME as CAPA_SHEET_NAME
from pyauditor.excel.capa import render_capa_sheet
from pyauditor.excel.glosas import Historico
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
    """Build the report workbook: cover (optional), CADASTROS (optional),
    INMS_BASE, group worksheets, GLOSAS, and EVIDENCIAS (optional).

    Each worksheet is built by its own module (ticket 09 SRP); this function
    only composes them in order. The caller owns the returned workbook.
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
            build_cadastros_sheet(workbook, configs)

        build_inms_base_sheet(workbook, competencia, summaries)
        build_group_sheets(workbook, summaries)

        effective_history = historico if historico is not None else {}
        build_glosas_sheet(
            workbook,
            competencia,
            summaries,
            valor_base,
            is_final_month=is_final_month,
            historico=effective_history,
        )

        if configs is not None:
            build_evidencias_sheet(
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
