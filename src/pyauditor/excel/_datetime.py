"""Parsing estruturado de datas vindas de CSV externo, para uso por qualquer
renderer de `excel/` que precise distinguir campo vazio de data malformada
em vez de descartar ambos silenciosamente como `None`. Também guarda a
tolerância padrão (em minutos) usada em comparações de prazo — não é um
detalhe do INMS 1.1, é um conceito de calendário/prazo reusável.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final

DATETIME_FMT: Final[str] = "%d/%m/%Y %H:%M"

# Tolerância padrão em comparações de prazo (arredondamento de minuto entre
# origens de dado diferentes) — não uma regra contratual.
PRAZO_TOLERANCIA_MINUTOS: Final[int] = 1


@dataclass(frozen=True)
class ParsedDateTime:
    value: datetime | None
    is_blank: bool
    is_malformed: bool


def parse_dt(raw: str) -> ParsedDateTime:
    """Distingue campo vazio (`is_blank`) de data malformada (`is_malformed`)
    — ao contrário de simplesmente devolver `None` para os dois casos, o que
    esconde erros de qualidade de dado do CSV de origem."""
    stripped = raw.strip()
    if not stripped:
        return ParsedDateTime(value=None, is_blank=True, is_malformed=False)
    try:
        value = datetime.strptime(stripped, DATETIME_FMT)
    except ValueError:
        return ParsedDateTime(value=None, is_blank=False, is_malformed=True)
    return ParsedDateTime(value=value, is_blank=False, is_malformed=False)
