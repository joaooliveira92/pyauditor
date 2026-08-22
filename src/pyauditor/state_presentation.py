"""Apresentação textual dos estados de comando — vocabulário neutro
compartilhado (ticket 06 SRP, etapa 6).

`orchestration/summary.py` e `interactive/flow.py` exibiam o mesmo mapa
`CommandState → (ícone, estilo)` cada um com sua cópia; vive aqui como fonte
única, sem dependência de camada (raiz, sem imports de `orchestration`/
`interactive`).
"""

from __future__ import annotations

from typing import Final

from pyauditor.orchestration.state import CommandState

__all__: Final[tuple[str, ...]] = (
    'STATE_PRESENTATION',
    'UNKNOWN_STATE_PRESENTATION',
)

STATE_PRESENTATION: Final[dict[CommandState, tuple[str, str]]] = {
    'pending': ('[ ]', 'dim'),
    'running': ('[>]', 'cyan'),
    'done': ('[x]', 'green'),
    'skipped': ('[~]', 'yellow'),
    'error': ('[!]', 'bold red'),
}

UNKNOWN_STATE_PRESENTATION: Final[tuple[str, str]] = (
    '[?]',
    'bold red',
)


def state_presentation(status: CommandState) -> tuple[str, str]:
    """Ícone e estilo de um estado de comando."""
    return STATE_PRESENTATION.get(status, UNKNOWN_STATE_PRESENTATION)
