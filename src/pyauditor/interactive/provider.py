"""Injeção do boundary de interação do fluxo guiado (ticket 10 SRP).

O contrato (`InteractionProvider`, `InteractionCancelledError`,
`MultiChoiceOption`, `TextValidator`) vive em `interactive/_contract.py` e a
implementação de produção (`RichQuestionaryProvider`) em
`interactive/rich_provider.py`. Este módulo reexporta ambos para preservar a
API pública (`from pyauditor.interactive.provider import ...`).

O fluxo guiado se comunica exclusivamente por `InteractionProvider`: prompts,
render de terminal e progresso ficam separados da orquestração e da regra de
negócio. Os providers tratam o texto dinâmico como literal (nunca markup) e
convertem cancelamento explícito em `InteractionCancelledError`.
"""

from __future__ import annotations

from typing import Final

from pyauditor.interactive._contract import (
    InteractionCancelledError,
    InteractionProvider,
    MultiChoiceOption,
    TextValidator,
)
from pyauditor.interactive.rich_provider import RichQuestionaryProvider

__all__: Final[tuple[str, ...]] = (
    'InteractionCancelledError',
    'InteractionProvider',
    'MultiChoiceOption',
    'RichQuestionaryProvider',
    'TextValidator',
)
