"""Mapa contratual Categoria → Nível (spec §14.5, anexo): dono único de
qual categoria pertence a qual Nível de atendimento (`N1`/`N2`/`N3`) e da
ordem de apresentação dos níveis. `excel/sintetico.py`, `excel/groups.py`
e `excel/inms_1_1_audit.py` importam daqui em vez de duplicar o mapa.

As chaves são as mesmas `categorias.yaml`/`GROUP_TABS`; categorias não
listadas caem fora do mapa (cada consumidor decide o fallback — sentinela
`—` no audit, agrupamento por Categoria no 1.14 etc.).
"""

from __future__ import annotations

from typing import Final

__all__: Final[tuple[str, ...]] = ("NIVEL_BY_CATEGORIA", "NIVEL_ORDER")

NIVEL_ORDER: Final[tuple[str, ...]] = ("N1", "N2", "N3")

NIVEL_BY_CATEGORIA: Final[dict[str, str]] = {
    "ATENDIMENTO_N1": "N1",
    "ATENDIMENTO_N2": "N2",
    "OPERACAO_N3": "N3",
    "MONITORAMENTO_NOC_SOC": "N3",
}
