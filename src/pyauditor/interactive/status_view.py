"""Apresentação de transições de estado na UI (ticket 05 SRP) — fora de
`interactive/flow.py`.

Extraído de `flow.py`: estado→(ícone, estilo) e a renderização de uma linha
de transição. O vocabulário de ícones/estilos é neutro e vive em
`pyauditor/state_presentation.py` (fonte única, compartilhada com o resumo
`orchestration/summary.py` — etapa 6).
"""

from __future__ import annotations

from typing import Final

from pyauditor.orchestration.state import CommandStateEntry
from pyauditor.state_presentation import STATE_PRESENTATION, state_presentation

__all__: Final[tuple[str, ...]] = (
    "STATE_PRESENTATION",
    "render_state_line",
)


def render_state_line(
    entry: CommandStateEntry,
) -> tuple[str, str]:
    """Build a literal status line and its separate presentation style.

    Markup is not embedded in the returned text. This allows providers to
    render command names and organization values literally.
    """
    icon, style = state_presentation(entry.status)
    orgao = entry.orgao or "consolidado"

    return (
        f"{icon} {entry.command} ({orgao})",
        style,
    )
