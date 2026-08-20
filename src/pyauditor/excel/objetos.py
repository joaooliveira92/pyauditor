"""`objetos.csv` — the contract's monetary source (ticket 07).

The capa lost its monetary fields; `input/objetos.csv` is now the single
source for the monthly value: one row per contractual item plus `TOTAL
MENSAL` and `TOTAL ANUAL` summary rows. `read_objetos` returns the per-item
monthly values (by item index, the `SERVICOS_POR_ORGAO` mapping key) and the
totals, validating the summary rows against the items:

- `total_mensal` is the authoritative `TOTAL MENSAL`; a mismatch with the
  sum of the items is a warning, not an error (the row is the fiscal's
  declaration, the items the breakdown — either can be stale).
- `total_anual` is checked against `total_mensal * 12`; divergence is a
  warning too.

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
OBJETOS_DELIMITER: Final = ";"
OBJETOS_ENCODING: Final = "utf-8-sig"

_ITEM_HEADER: Final = "Item"
_CATEGORIA_HEADER: Final = "Categoria"
_VALOR_HEADER: Final = "Valor Mensal do Contrato 40/2022"

_TOTAL_MENSAL_ROW: Final = "TOTAL MENSAL"
_TOTAL_ANUAL_ROW: Final = "TOTAL ANUAL"

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
        ValueError: if the file is malformed (wrong header, missing TOTAL
            rows, unparseable money, non-monotonic item indices). The CLI
            treats malformed input as a technical failure (ticket 07 Q5);
            a *missing* file is incomplete data, decided by the caller.
    """
    with path.open(encoding=OBJETOS_ENCODING, newline="") as handle:
        reader = csv.DictReader(handle, delimiter=OBJETOS_DELIMITER)
        if reader.fieldnames is None:
            raise ValueError(f"{path}: CSV vazio ou sem cabeçalho")
        fieldnames = [name.strip() for name in reader.fieldnames]
        if set(fieldnames) != {_ITEM_HEADER, _CATEGORIA_HEADER, _VALOR_HEADER}:
            raise ValueError(
                f"{path}: cabeçalho esperado '{';'.join((_ITEM_HEADER, _CATEGORIA_HEADER, _VALOR_HEADER))}'"
            )
        rows = list(reader)

    itens: list[tuple[int, float]] = []
    total_mensal: float | None = None
    total_anual: float | None = None
    for row in rows:
        item_raw = row[_ITEM_HEADER].strip()
        valor_raw = row[_VALOR_HEADER].strip()

        if item_raw == _TOTAL_MENSAL_ROW:
            total_mensal = parse_brl_value(valor_raw)
            continue
        if item_raw == _TOTAL_ANUAL_ROW:
            total_anual = parse_brl_value(valor_raw)
            continue

        if not item_raw.isdigit():
            raise ValueError(f"{path}: linha sem item numérico: {item_raw!r}")
        item = int(item_raw)
        if item < 1:
            raise ValueError(f"{path}: índice de item inválido: {item}")
        itens.append((item, parse_brl_value(valor_raw)))

    if total_mensal is None:
        raise ValueError(f"{path}: linha '{_TOTAL_MENSAL_ROW}' ausente")
    if total_anual is None:
        raise ValueError(f"{path}: linha '{_TOTAL_ANUAL_ROW}' ausente")

    itens.sort()
    expected = tuple(i for i, _ in itens)
    if expected != tuple(range(1, len(itens) + 1)):
        raise ValueError(f"{path}: índices de item não contíguos: {expected}")

    warnings: list[str] = []
    soma = sum(valor for _, valor in itens)
    if abs(soma - total_mensal) > 0.01:
        warnings.append(
            f"'{_TOTAL_MENSAL_ROW}' ({total_mensal:,.2f}) diverge da soma dos itens ({soma:,.2f})"
        )
    esperado_anual = total_mensal * 12
    if abs(esperado_anual - total_anual) > 0.01:
        warnings.append(
            f"'{_TOTAL_ANUAL_ROW}' ({total_anual:,.2f}) diverge de '{_TOTAL_MENSAL_ROW}' × 12 ({esperado_anual:,.2f})"
        )

    return Objetos(
        itens=tuple(valor for _, valor in itens),
        total_mensal=total_mensal,
        total_anual=total_anual,
        warnings=tuple(warnings),
    )