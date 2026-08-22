"""Fachada do consolidado financeiro — API pública preservada após a divisão
do módulo (ticket 04 SRP): `workbook.py` mantém os builders de aba e a
orquestração; `_glosa_calcs` e `_decisions_io` abrigam aritmética/I/O puros.
`cli/consolidate.py` e os testes importam daqui sem mudança.
"""

from pyauditor.excel.consolidate.workbook import (
    CALCULO_SHEET,
    CAPA_SHEET,
    GLOSAS_SHEET,
    INMS_BASE_SHEET,
    SERVICOS_SHEET,
    build_consolidated_workbook,
    read_existing_decisions,
)

__all__ = (
    'CALCULO_SHEET',
    'CAPA_SHEET',
    'GLOSAS_SHEET',
    'INMS_BASE_SHEET',
    'SERVICOS_SHEET',
    'build_consolidated_workbook',
    'read_existing_decisions',
)
