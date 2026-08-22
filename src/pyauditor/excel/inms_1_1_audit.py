"""Fachada da aba "INMS 1.1" enriquecida — API pública preservada após o split
SRP (ticket 04): a implementação vive em `excel/inms_1_1/*` (`write.py` +
`_layout`/`_cells`/`_domain`/`_raw_block`/`_sections_*`). `sintetico.py` e os
testes continuam importando `has_required_columns`/`write_sheet` daqui.

`_build_grupo_rows`/`_SEM_NIVEL` são reexportados por compatibilidade com a
suíte existente de `test_inms_1_1_audit.py` (testes unitários de resolução de
grupos/nível).
"""

from __future__ import annotations

from typing import Final

from pyauditor.excel.inms_1_1._domain import _build_grupo_rows
from pyauditor.excel.inms_1_1._layout import _SEM_NIVEL
from pyauditor.excel.inms_1_1.write import has_required_columns, write_sheet

__all__: Final[tuple[str, ...]] = (
    "_SEM_NIVEL",
    "_build_grupo_rows",
    "has_required_columns",
    "write_sheet",
)
