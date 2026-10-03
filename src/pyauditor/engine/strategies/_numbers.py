"""Helpers de parsing numérico compartilhados pelas strategies de cálculo.

Os datasets reais são exports PT-BR: delimiter `;` com **vírgula** como
separador decimal (`99,451`). `float()` não parseia isso, então as strategies
roteiam toda coluna numérica por :func:`parse_decimal`.
"""

from __future__ import annotations

import math


def parse_decimal(raw: str) -> float:
    """Parseia um decimal em formato PT-BR (vírgula como separador) para
    ``float``.

    ``"99,451"`` -> ``99.451``; ``"0"`` simples e valores com ponto também
    funcionam. Devolve ``nan`` para entrada ilegível (chamadores pulam em
    ``nan``).
    """
    if not raw:
        return math.nan
    s = raw.strip()
    if not s:
        return math.nan
    if ',' in s:
        s = s.replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return math.nan


def as_float(value: object) -> float | None:
    """`None` a menos que *value* seja número real — `bool` é subclasse de
    `int` em Python, então é excluído explicitamente em vez de silenciosamente
    convertido em `1.0`/`0.0`."""
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    return None
