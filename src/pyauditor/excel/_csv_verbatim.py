"""Leitura crua de CSV para reprodução verbatim como aba de Excel — sem
nenhum processamento, cabeçalho + linhas tal qual estão no arquivo. Usado
pelas abas "Prazos"/"Capa"/"Equipe"/"Objetos" de `sintetico.xlsx`
(`excel/sintetico.py`), cada uma com seu próprio delimiter/encoding.
"""

from __future__ import annotations

import csv
from pathlib import Path


def read_csv_verbatim(
    path: Path, *, delimiter: str, encoding: str
) -> tuple[list[str], list[list[str]]]:
    """Lê um CSV cru: (cabeçalho, linhas).

    Raises:
        FileNotFoundError: arquivo ausente — decisão do chamador (warning,
            aba não gerada).
        ValueError: CSV vazio (sem nem cabeçalho).
    """
    with path.open(encoding=encoding, newline='') as handle:
        rows = list(csv.reader(handle, delimiter=delimiter))
    if not rows:
        raise ValueError(f'{path}: CSV vazio')
    return rows[0], rows[1:]
