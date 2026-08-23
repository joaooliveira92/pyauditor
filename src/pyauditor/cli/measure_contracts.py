"""Contratos compartilhados de `cli/measure` (ticket 07 SRP).

Os dataclasses de resultado/coleta e o helper de nome seguro de arquivo vivem
aqui para que `cli/measure.py` e `cli/measure_run.py` os importem sem ciclo de
import. `cli/measure.py` reexporta via import preservando a API pública.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from pyauditor.engine.pipeline import MeasurementResult

__all__: Final[tuple[str, ...]] = (
    'IndicatorOutcome',
    '_MeasuredIndicator',
    '_sanitize_indicator_id',
)

_UNSAFE_ID_CHARS_RE: Final = re.compile(r'[^A-Za-z0-9._-]')


@dataclass(frozen=True, slots=True)
class IndicatorOutcome:
    contractual_id: str
    rom_path: Path
    summary_path: Path
    hard_failure: bool
    error: str | None
    not_activated: bool = False


@dataclass(frozen=True, slots=True)
class _MeasuredIndicator:
    """Indicador medido + cells de Responsáveis do seu órgão."""

    indicator_id: str
    safe_id: str
    orgao: str
    result: MeasurementResult
    capa_fields: dict[str, object]


def _sanitize_indicator_id(raw: str) -> str:
    """Cria um nome de arquivo seguro sem escapar do diretório de saída."""
    sanitized = _UNSAFE_ID_CHARS_RE.sub('_', raw).strip('._')
    return sanitized or '_indicator'
