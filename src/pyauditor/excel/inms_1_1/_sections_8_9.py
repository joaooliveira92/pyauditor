"""Seções 8–9 da aba INMS 1.1 (tempo corrido, penalidade). Ambas são
genéricas para qualquer shape de ratio único (INMS 1.1, INMS 1.3) e moram
em `excel/_inms_audit_common/` — reexportadas aqui com os nomes que
`inms_1_1/write.py` já usa.
"""

from __future__ import annotations

from pyauditor.excel._inms_audit_common._section_8 import (
    write_section_8_tempo as _write_section_8_tempo,
)
from pyauditor.excel._inms_audit_common._section_9 import (
    write_section_9_penalidade_ratio as _write_section_9_penalidade,
)

__all__ = ('_write_section_8_tempo', '_write_section_9_penalidade')
