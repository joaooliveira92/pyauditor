"""Apresentação de transições de estado na UI (ticket 05 SRP) — fora de
`interactive/flow.py`.

Extraído de `flow.py`: estado→(ícone, estilo) e a renderização de uma linha de
transição. Deduplicar com `summary.py:69-75` é débito registrado da etapa 6.
"""

from __future__ import annotations

from typing import Final

from pyauditor.orchestration.state import CommandState, CommandStateEntry

__all__: Final[tuple[str, ...]] = (
    "STATE_PRESENTATION",
    "render_state_line",
)

STATE_PRESENTATION: Final[dict[CommandState, tuple[str, str]]] = {
    "pending": ("[ ]", "dim"),
    "running": ("[>]", "cyan"),
    "done": ("[x]", "green"),
    "skipped": ("[~]", "yellow"),
    "error": ("[!]", "bold red"),
}

_UNKNOWN_STATE_PRESENTATION: Final[tuple[str, str]] = (
    "[?]",
    "bold red",
)


def render_state_line(
    entry: CommandStateEntry,
) -> tuple[str, str]:
    """Build a literal status line and its separate presentation style.

    Markup is not embedded in the returned text. This allows providers to
    render command names and organization values literally.
    """
    icon, style = STATE_PRESENTATION.get(
        entry.status,
        _UNKNOWN_STATE_PRESENTATION,
    )
    orgao = entry.orgao or "consolidado"

    return (
        f"{icon} {entry.command} ({orgao})",
        style,
    )