"""Constantes de leiaute da aba INMS 1.1 — as genéricas (compartilhadas com
outras abas enriquecidas, ex. INMS 1.2) vivem em
`excel/_inms_audit_common/_layout.py` e são reexportadas aqui com os nomes
que o resto do pacote já usa; só a constante de prazo contratual bruto (2h
corridas, específica de incidentes) é definida localmente.
"""

from __future__ import annotations

from typing import Final

from pyauditor.excel._inms_audit_common._layout import (
    AA as _AA,
)
from pyauditor.excel._inms_audit_common._layout import (
    AB as _AB,
)
from pyauditor.excel._inms_audit_common._layout import (
    AC as _AC,
)
from pyauditor.excel._inms_audit_common._layout import (
    AD as _AD,
)
from pyauditor.excel._inms_audit_common._layout import (
    AE as _AE,
)
from pyauditor.excel._inms_audit_common._layout import (
    AF as _AF,
)
from pyauditor.excel._inms_audit_common._layout import (
    AG as _AG,
)
from pyauditor.excel._inms_audit_common._layout import (
    AH as _AH,
)
from pyauditor.excel._inms_audit_common._layout import (
    AI as _AI,
)
from pyauditor.excel._inms_audit_common._layout import (
    AJ as _AJ,
)
from pyauditor.excel._inms_audit_common._layout import (
    AK as _AK,
)
from pyauditor.excel._inms_audit_common._layout import (
    AL as _AL,
)
from pyauditor.excel._inms_audit_common._layout import (
    AM as _AM,
)
from pyauditor.excel._inms_audit_common._layout import (
    AN as _AN,
)
from pyauditor.excel._inms_audit_common._layout import (
    AO as _AO,
)
from pyauditor.excel._inms_audit_common._layout import (
    AP as _AP,
)
from pyauditor.excel._inms_audit_common._layout import (
    AQ as _AQ,
)
from pyauditor.excel._inms_audit_common._layout import (
    ATIVIDADE_COLUMN as _ATIVIDADE_COLUMN,
)
from pyauditor.excel._inms_audit_common._layout import (
    AUDIT_REVIEW_LABEL as _AUDIT_REVIEW_LABEL,
)
from pyauditor.excel._inms_audit_common._layout import (
    BODY_FONT,
    BORDER,
    GRAY_FILL,
    GREEN_FILL,
    HEADER_FILL,
    HEADER_FONT,
    LABEL_FONT,
    NOTE_FONT,
    ORANGE_FILL,
    RED_FILL,
    SECTION_FILL,
    SECTION_FONT,
    TEAL_FILL,
    TITLE_FONT,
)
from pyauditor.excel._inms_audit_common._layout import (
    DATA_FIM_COLUMN as _DATA_FIM_COLUMN,
)
from pyauditor.excel._inms_audit_common._layout import (
    DATA_LIMITE_COLUMN as _DATA_LIMITE_COLUMN,
)
from pyauditor.excel._inms_audit_common._layout import (
    DATA_QUALIDADE_OK as _DATA_QUALIDADE_OK,
)
from pyauditor.excel._inms_audit_common._layout import (
    DATA_SOLICITACAO_COLUMN as _DATA_SOLICITACAO_COLUMN,
)
from pyauditor.excel._inms_audit_common._layout import (
    DATE_FMT as _DATE_FMT,
)
from pyauditor.excel._inms_audit_common._layout import (
    DATETIME_FMT as _DATETIME_FMT,
)
from pyauditor.excel._inms_audit_common._layout import (
    DUR as _DUR,
)
from pyauditor.excel._inms_audit_common._layout import (
    INCLUIDO_NAO as _INCLUIDO_NAO,
)
from pyauditor.excel._inms_audit_common._layout import (
    INCLUIDO_SIM as _INCLUIDO_SIM,
)
from pyauditor.excel._inms_audit_common._layout import (
    NIVEL_BY_CATEGORIA_ as _NIVEL_BY_CATEGORIA,
)
from pyauditor.excel._inms_audit_common._layout import (
    NIVEL_ORDER_ as _NIVEL_ORDER,
)
from pyauditor.excel._inms_audit_common._layout import (
    NO_PRAZO_COLUMN as _NO_PRAZO_COLUMN,
)
from pyauditor.excel._inms_audit_common._layout import (
    NUM_SOLICITACAO_COLUMN as _NUM_SOLICITACAO_COLUMN,
)
from pyauditor.excel._inms_audit_common._layout import (
    PCT2 as _PCT2,
)
from pyauditor.excel._inms_audit_common._layout import (
    PCT4 as _PCT4,
)
from pyauditor.excel._inms_audit_common._layout import (
    SEM_NIVEL as _SEM_NIVEL,
)
from pyauditor.excel._inms_audit_common._layout import (
    TECNICO_COLUMN as _TECNICO_COLUMN,
)
from pyauditor.excel._inms_audit_common._layout import (
    UNLOCKED as _UNLOCKED,
)
from pyauditor.excel._inms_audit_common._layout import (
    R as _R,
)
from pyauditor.excel._inms_audit_common._layout import (
    S as _S,
)
from pyauditor.excel._inms_audit_common._layout import (
    T as _T,
)
from pyauditor.excel._inms_audit_common._layout import (
    U as _U,
)
from pyauditor.excel._inms_audit_common._layout import (
    V as _V,
)
from pyauditor.excel._inms_audit_common._layout import (
    W as _W,
)
from pyauditor.excel._inms_audit_common._layout import (
    X as _X,
)
from pyauditor.excel._inms_audit_common._layout import (
    Y as _Y,
)
from pyauditor.excel._inms_audit_common._layout import (
    Z as _Z,
)

__all__ = (
    'BODY_FONT',
    'BORDER',
    'GRAY_FILL',
    'GREEN_FILL',
    'HEADER_FILL',
    'HEADER_FONT',
    'LABEL_FONT',
    'NOTE_FONT',
    'ORANGE_FILL',
    'RED_FILL',
    'SECTION_FILL',
    'SECTION_FONT',
    'TEAL_FILL',
    'TITLE_FONT',
    '_AA',
    '_AB',
    '_AC',
    '_AD',
    '_AE',
    '_AF',
    '_AG',
    '_AH',
    '_AI',
    '_AJ',
    '_AK',
    '_AL',
    '_AM',
    '_AN',
    '_AO',
    '_AP',
    '_AQ',
    '_ATIVIDADE_COLUMN',
    '_AUDIT_REVIEW_LABEL',
    '_DATA_FIM_COLUMN',
    '_DATA_LIMITE_COLUMN',
    '_DATA_QUALIDADE_OK',
    '_DATA_SOLICITACAO_COLUMN',
    '_DATETIME_FMT',
    '_DATE_FMT',
    '_DUR',
    '_INCLUIDO_NAO',
    '_INCLUIDO_SIM',
    '_NIVEL_BY_CATEGORIA',
    '_NIVEL_ORDER',
    '_NO_PRAZO_COLUMN',
    '_NUM_SOLICITACAO_COLUMN',
    '_PCT2',
    '_PCT4',
    '_PRAZO_HORAS_CORRIDAS',
    '_R',
    '_S',
    '_SEM_NIVEL',
    '_T',
    '_TECNICO_COLUMN',
    '_U',
    '_UNLOCKED',
    '_V',
    '_W',
    '_X',
    '_Y',
    '_Z',
)

# Prazo contratual de incidentes de criticidade alta (Anexo D / aba
# "Prazos" — input/prazos.csv: "Incidentes, Alta, 2h (horas corridas)").
# Constante local: só esta aba precisa do valor numérico para o controle
# contratual bruto; nenhum outro shape do pipeline usa "2 horas corridas"
# (o INMS 1.2 tem prazo variável por SLA e não recalcula esse controle —
# ver `excel/_inms_audit_common/_raw_block.py`).
_PRAZO_HORAS_CORRIDAS: Final[float] = 2.0
