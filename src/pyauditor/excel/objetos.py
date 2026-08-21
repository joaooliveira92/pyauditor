"""`objetos.csv` — the contract's monetary source (ticket 07).

The capa lost its monetary fields; `input/objetos.csv` is now the single
source for the monthly value: one row per contractual item (`Item,
Categoria, Valor`). `read_objetos` returns the per-item monthly values (by
item index, the `SERVICOS_POR_ORGAO` mapping key) and the totals — both
`total_mensal` and `total_anual` are derived by summing the items (x1 and
x12 respectively): the file carries no separate fiscal-declared summary row
to cross-check against.

Values arrive as pt-BR currency text (`R$ 148.205,54`); the parser accepts
that shape (optional `R$`, thousands `.`, decimal `,`) and stores `float`.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final

OBJETOS_FILENAME: Final = "objetos.csv"
OBJETOS_DELIMITER: Final = ","
OBJETOS_ENCODING: Final = "utf-8-sig"

_ITEM_HEADER: Final = "Item"
_CATEGORIA_HEADER: Final = "Categoria"
_VALOR_HEADER: Final = "Valor"

_MONEY_RE: Final = re.compile(r"^\s*R?\$?\s*([\d.,]+)\s*$")


@dataclass(frozen=True, slots=True)
class Objetos:
    """Parsed `objetos.csv`: per-item monthly values plus the totals."""

    itens: tuple[float, ...]  # valor mensal por item contratual (índice 1..N)
    total_mensal: float
    total_anual: float
    warnings: tuple[str, ...]


def parse_brl_value(text: str) -> float:
    """Parses pt-BR currency text like `R$ 148.205,54` (or `148205.54`) into
    a float. `R$` prefix, spaces, thousands `.` and decimal `,` are all
    accepted; a plain machine number round-trips unchanged."""
    match = _MONEY_RE.match(text)
    if match is None:
        raise ValueError(f"valor monetário inválido: {text!r}")
    digits = match.group(1).strip()
    if "," in digits:
        digits = digits.replace(".", "").replace(",", ".")
        return float(digits)
    return float(digits.replace(",", ""))


def read_objetos(path: Path) -> Objetos:
    """Reads and validates `objetos.csv`.

    Raises:
        ValueError: if the file is malformed (wrong header, unparseable
            money, non-monotonic item indices). The CLI treats malformed
            input as a technical failure (ticket 07 Q5); a *missing* file
            is incomplete data, decided by the caller.
    """
    with path.open(encoding=OBJETOS_ENCODING, newline="") as handle:
        reader = csv.DictReader(handle, delimiter=OBJETOS_DELIMITER)
        if reader.fieldnames is None:
            raise ValueError(f"{path}: CSV vazio ou sem cabeçalho")
        fieldnames = [name.strip() for name in reader.fieldnames]
        if set(fieldnames) != {_ITEM_HEADER, _CATEGORIA_HEADER, _VALOR_HEADER}:
            raise ValueError(
                f"{path}: cabeçalho esperado "
                f"'{OBJETOS_DELIMITER.join((_ITEM_HEADER, _CATEGORIA_HEADER, _VALOR_HEADER))}'"
            )
        rows = list(reader)

    itens: list[tuple[int, float]] = []
    for row in rows:
        item_raw = row[_ITEM_HEADER].strip()
        valor_raw = row[_VALOR_HEADER].strip()

        if not item_raw.isdigit():
            raise ValueError(f"{path}: linha sem item numérico: {item_raw!r}")
        item = int(item_raw)
        if item < 1:
            raise ValueError(f"{path}: índice de item inválido: {item}")
        itens.append((item, parse_brl_value(valor_raw)))

    itens.sort()
    expected = tuple(i for i, _ in itens)
    if expected != tuple(range(1, len(itens) + 1)):
        raise ValueError(f"{path}: índices de item não contíguos: {expected}")

    total_mensal = sum(valor for _, valor in itens)
    return Objetos(
        itens=tuple(valor for _, valor in itens),
        total_mensal=total_mensal,
        total_anual=total_mensal * 12,
        warnings=(),
    )