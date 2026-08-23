"""Fachada do dispatcher de `sintetico.xlsx` — ver `_build` para a divisão
por responsabilidade do pacote. `sintetico/__init__.py` e os testes importam
`write_sintetico_workbook` daqui, sem mudança de API após a divisão em
módulos (SRP)."""

from __future__ import annotations

from typing import Final

from ._build import write_sintetico_workbook

__all__: Final[tuple[str, ...]] = ('write_sintetico_workbook',)
