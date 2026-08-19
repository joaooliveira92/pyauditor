"""Numeric parsing helpers shared by the calculation strategies.

The real datasets are PT-BR exports: `;`-delimited with **comma** as the
decimal separator (`99,451`). ``float()`` can't parse that, so the strategies
route any numeric column through :func:`parse_decimal`.
"""

from __future__ import annotations

from typing import Final


def parse_decimal(raw: str) -> float:
    """Parse a PT-BR decimal string (comma decimal separator) to ``float``.

    ``"99,451"`` -> ``99.451``; plain ``"0"`` and dot-separated values also
    work. Returns ``nan`` for unparseable input (callers skip on ``nan``).
    """
    value = raw.strip().replace(",", ".")
    try:
        return float(value)
    except ValueError:
        return float("nan")
