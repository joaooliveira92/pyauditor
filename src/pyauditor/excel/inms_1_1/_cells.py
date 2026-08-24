"""Primitivas de célula/fórmula da aba INMS 1.1 — movidas para
`excel/_inms_audit_common/_cells.py` (compartilhadas com outras abas
enriquecidas, ex. INMS 1.2) e reexportadas aqui com os nomes que o resto do
pacote já usa.
"""

from __future__ import annotations

from pyauditor.excel._inms_audit_common._cells import (
    CellValue as _CellValue,
)
from pyauditor.excel._inms_audit_common._cells import (
    ColumnRange as _ColumnRange,
)
from pyauditor.excel._inms_audit_common._cells import (
    add_situacao_conditional_formatting as _add_situacao_conditional_formatting,
)
from pyauditor.excel._inms_audit_common._cells import (
    add_table as _add_table,
)
from pyauditor.excel._inms_audit_common._cells import (
    apply_section_outline as _apply_section_outline,
)
from pyauditor.excel._inms_audit_common._cells import (
    header_row as _header_row,
)
from pyauditor.excel._inms_audit_common._cells import (
    label_value as _label_value,
)
from pyauditor.excel._inms_audit_common._cells import (
    protect_support_columns as _protect_support_columns,
)
from pyauditor.excel._inms_audit_common._cells import (
    raw_range as _raw_range,
)
from pyauditor.excel._inms_audit_common._cells import (
    section_bar as _section_bar,
)

__all__ = (
    '_CellValue',
    '_ColumnRange',
    '_add_situacao_conditional_formatting',
    '_add_table',
    '_apply_section_outline',
    '_header_row',
    '_label_value',
    '_protect_support_columns',
    '_raw_range',
    '_section_bar',
)
