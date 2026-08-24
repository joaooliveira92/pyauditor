"""Seções 4–5 da aba INMS 1.1 (detalhamento por grupo, subtotais) — movidas
para `excel/_inms_audit_common/_sections_4_5.py` (compartilhadas com outras
abas enriquecidas, ex. INMS 1.2) e reexportadas aqui com os nomes que o
resto do pacote já usa.
"""

from __future__ import annotations

from pyauditor.excel._inms_audit_common._sections_4_5 import (
    write_section_4_detalhamento as _write_section_4_detalhamento,
)
from pyauditor.excel._inms_audit_common._sections_4_5 import (
    write_section_5_subtotais as _write_section_5_subtotais,
)

__all__ = ('_write_section_4_detalhamento', '_write_section_5_subtotais')
