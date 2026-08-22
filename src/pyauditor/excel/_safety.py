"""Sanitização de texto não confiável para células do Excel — usado por
qualquer renderer de `excel/` que grave texto vindo de CSV/YAML externo
(dado bruto, não fórmula gerada internamente pelo próprio módulo).
"""

from __future__ import annotations

_FORMULA_PREFIXES: tuple[str, ...] = ("=", "+", "-", "@")


def safe_excel_text(value: str) -> str:
    """Neutraliza formula injection: se `value` começar com um caractere que
    o Excel interpreta como início de fórmula, prefixa com apóstrofo para
    forçar interpretação como texto literal. Não usar em valores onde o
    próprio módulo grava fórmulas de propósito."""
    if value.startswith(_FORMULA_PREFIXES):
        return f"'{value}"
    return value
