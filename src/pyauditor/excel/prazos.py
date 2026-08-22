"""`prazos.csv` (`input/prazos.csv`) — tabela de referência de SLA por
tipo/criticidade de demanda, compartilhada entre órgãos. Reproduzida
verbatim como a primeira aba de `sintetico.xlsx`, a pedido do usuário: não
há processamento, só leitura crua e regravação linha a linha.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Final

PRAZOS_FILENAME: Final = "prazos.csv"
PRAZOS_SHEET_NAME: Final = "Prazos"
_PRAZOS_DELIMITER: Final = ","
_PRAZOS_ENCODING: Final = "utf-8-sig"


def read_prazos(path: Path) -> tuple[list[str], list[list[str]]]:
    """Lê `prazos.csv` cru.

    Raises:
        FileNotFoundError: arquivo ausente — decisão do chamador (warning,
            aba não gerada), mesmo contrato de `equipe.read_equipe`.
        ValueError: CSV vazio (sem nem cabeçalho).
    """
    with path.open(encoding=_PRAZOS_ENCODING, newline="") as handle:
        rows = list(csv.reader(handle, delimiter=_PRAZOS_DELIMITER))
    if not rows:
        raise ValueError(f"{path}: CSV vazio")
    return rows[0], rows[1:]
