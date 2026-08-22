"""Fachada do `sintetico.xlsx` (spec §14.4) — API pública preservada após a
divisão do módulo em `workbook.py` (dispatcher + renderers) e `_stats.py`
(aritmética pura). `cli/split.py` e os testes importam daqui sem mudança.
"""

from pyauditor.excel.sintetico.workbook import write_sintetico_workbook

__all__ = ('write_sintetico_workbook',)
