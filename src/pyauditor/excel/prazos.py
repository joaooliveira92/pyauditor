"""`prazos.csv` (`input/prazos.csv`) — tabela de referência de SLA por
tipo/criticidade de demanda, compartilhada entre órgãos. Lida crua aqui;
`excel/sintetico/_sheets/institutional.py` aplica a formatação institucional
(título, cores de criticidade, padronização de texto) da aba "Prazos" de
`sintetico.xlsx`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from pyauditor.excel._csv_verbatim import read_csv_verbatim

PRAZOS_FILENAME: Final = 'prazos.csv'
PRAZOS_SHEET_NAME: Final = 'Prazos'
PRAZOS_DELIMITER: Final = ','
PRAZOS_ENCODING: Final = 'utf-8-sig'


def read_prazos(path: Path) -> tuple[list[str], list[list[str]]]:
    """Lê `prazos.csv` cru.

    Raises:
        FileNotFoundError: arquivo ausente — decisão do chamador (warning,
            aba não gerada), mesmo contrato de `equipe.read_equipe`.
        ValueError: CSV vazio (sem nem cabeçalho).
    """
    return read_csv_verbatim(
        path, delimiter=PRAZOS_DELIMITER, encoding=PRAZOS_ENCODING
    )
