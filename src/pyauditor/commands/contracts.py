"""Contratos de resultado dos comandos do pipeline (ticket 11 SRP).

Neutro em relação às camadas: as dataclasses de resultado do `run_*` de cada
comando (`BootstrapResult`, `MeasureResult`, `SplitResult`, `ReportResult`,
`ConsolidateResult`) e os helpers de código de saída vivem aqui para que
`orchestration/summary*.py` dependam do contrato, e não de módulos `cli/*`.

Cada `cli/<comando>.py` reexporta a sua dataclass (via import) preservando a
API pública; `cli/results.py` mantém `Status`/`ExitCode`/hints, reimportados
neste módulo.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Protocol

from pyauditor.cli.results import Status, exit_code_name, is_production_command

__all__: Final[tuple[str, ...]] = (
    'BootstrapResult',
    'ConsolidateResult',
    'IndicatorOutcome',
    'MeasureResult',
    'ReportResult',
    'SplitCategoriaOutcome',
    'SplitResult',
    'exit_code_for_results',
    'exit_code_name',
    'is_production_command',
)


@dataclass(frozen=True, slots=True)
class IndicatorOutcome:
    contractual_id: str
    rom_path: Path
    summary_path: Path
    hard_failure: bool
    error: str | None
    not_activated: bool = False


@dataclass(frozen=True, slots=True)
class BootstrapResult:
    status: Status
    orgao: str
    capa_path: Path  # CSV do órgão (o destino por-órgão)
    created: bool  # True se algum arquivo (comum ou do órgão) foi criado
    warnings: tuple[str, ...]
    error_message: str | None


@dataclass(frozen=True, slots=True)
class MeasureResult:
    status: Status
    competencia: str
    orgao: str
    indicators: tuple[IndicatorOutcome, ...]
    warnings: tuple[str, ...]
    error_message: str | None


@dataclass(frozen=True, slots=True)
class SplitCategoriaOutcome:
    inms: str
    categoria: str
    csv_path: Path
    config_path: Path | None  # None só para `outros` (sem config derivada)
    row_count: int


@dataclass(frozen=True, slots=True)
class SplitResult:
    status: Status
    competencia: str
    orgao: str
    categorias: tuple[SplitCategoriaOutcome, ...]
    warnings: tuple[str, ...]
    error_message: str | None
    sintetico_path: Path | None = None


@dataclass(frozen=True, slots=True)
class ReportResult:
    status: Status
    competencia: str
    orgao: str
    output_path: Path
    indicator_count: int
    warnings: tuple[str, ...]
    error_message: str | None
    publicable: bool = True
    glosa_calculada: bool = True


@dataclass(frozen=True, slots=True)
class ConsolidateResult:
    status: Status
    competencia: str
    output_path: Path
    decisions_preserved: int
    warnings: tuple[str, ...]
    error_message: str | None
    glosa_calculada: bool = True
    total_pontos: float = 0.0


class _HasResult(Protocol):
    @property
    def status(self) -> Status: ...


def exit_code_for_results(results: Sequence[_HasResult]) -> int:
    """Reduz um fan-out (`--orgao both`) de `report`/`consolidate` a um
    código, pela precedência `1 > 4 > 3 > 0`. Para `bootstrap`/`measure`
    (sem sinais de 3/4) reduz-se ao comportamento anterior: `1` se algum
    resultado errou, senão `0`."""
    if any(result.status == 'error' for result in results):
        return 1
    if _has_financial_issue(results):
        return 4
    if _has_publication_issue(results):
        return 3
    return 0


def _has_financial_issue(results: Sequence[_HasResult]) -> bool:
    """`True` se algum resultado sinaliza glosa monetária não calculada
    (ticket 01) — o `glosa_calculada: bool` dos resultados de report/
    consolidate; `bootstrap`/`measure` não carregam o atributo (None)."""
    return any(
        getattr(result, 'glosa_calculada', True) is False for result in results
    )


def _has_publication_issue(results: Sequence[_HasResult]) -> bool:
    """`True` se algum resultado é não-publicável (rascunho — obrigatórios
    para publicar ausentes, ticket 02). Idem: só quem carrega `publicable`
    participa; o resto ignora o atributo."""
    return any(
        getattr(result, 'publicable', True) is False for result in results
    )
