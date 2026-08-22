"""Shared vocabulary for `run_*` results (ticket "Structured result
dataclasses", .scratch/interactive-cli map). `Status` only knows `done`/
`error` — that's a completed call's outcome, distinct from the fuller
Command state (pending/running/done/skipped/error) orchestration tracks.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final, Literal, Protocol

_COMPETENCIA_RE: Final = re.compile(r'^\d{4}-\d{2}$')

# Ticket "11 - Tratamento de diretório sem permissão / arquivo bloqueado":
# `PermissionError` (diretório sem escrita) e Excel aberto/bloqueado por
# outro processo chegam ambos como `OSError`, indistinguíveis de forma
# confiável a partir da exceção — a dica cobre as duas causas sem tentar
# adivinhar qual é (`atomic_write` já garante que nada fica corrompido; isto
# só melhora a mensagem). Cada chamador já monta sua própria mensagem
# ("falha ao escrever X: exc") — só aponta esta dica no final.
WRITE_FAILURE_HINT: Final = (
    'verifique as permissões do diretório ou se o arquivo está aberto em '
    'outro programa'
)
DIR_FAILURE_HINT: Final = 'verifique as permissões do diretório'


def validate_competencia(competencia: str) -> str | None:
    """`None` if *competencia* is `YYYY-MM`; otherwise an actionable error
    message. Every subcommand that turns `competencia` into a filesystem
    path (`measure`/`report`/`consolidate`/`run`) must call this before
    building any path from it."""
    if not _COMPETENCIA_RE.match(competencia):
        return (
            f'competência inválida {competencia!r}: esperado YYYY-MM '
            '(ex.: 2026-06)'
        )
    return None


type Status = Literal['done', 'error']

# Contrato de códigos de saída (ticket "03 - Contrato de códigos de saída",
# .scratch/ajuste-cli). Precedência global: 1 > 4 > 3 > 0; 2 é exclusivo do
# parse (argparse / `main.py`), nunca coexiste com resultado de run.
type ExitCode = Literal[0, 1, 2, 3, 4]

_EXIT_CODES: Final[dict[Status, int]] = {'done': 0, 'error': 1}


def exit_code_for(status: Status) -> int:
    return _EXIT_CODES[status]


# Rótulo estável por código — o resumo final (ticket 04) exibe exatamente
# este nome, para o resumo e o código de saída nunca divergirem na leitura
# do estado global da execução.
_EXIT_NAMES: Final[dict[int, str]] = {
    0: 'CONCLUÍDO',
    1: 'FALHA',
    2: 'USO INVÁLIDO',
    3: 'CONCLUÍDO COM PENDÊNCIAS',
    4: 'CÁLCULO FINANCEIRO INDISPONÍVEL',
}

# Comandos que produzem artefato financeiro/publicável — só eles podem
# emitir 3/4. `bootstrap`/`measure` não têm semântica de publicação: ficam
# em 0/1. Um `skipped` destes sinaliza o código global para 3 (resultado
# financeiro incompleto nunca vale `0`).
_PRODUCTION_COMMANDS: Final[frozenset[str]] = frozenset(
    {'report', 'consolidate'}
)


def exit_code_name(code: int) -> str:
    return _EXIT_NAMES[code]


def is_production_command(command: str) -> bool:
    return command in _PRODUCTION_COMMANDS


class _HasResult(Protocol):
    @property
    def status(self) -> Status: ...


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


@dataclass(frozen=True, slots=True)
class DependencyCheck:
    """Result of a Command's precondition check (ticket "Dependency
    enforcement") — lives here, not in `cli/dependencies.py`, so each
    command file (which returns one) doesn't import from the registry
    that imports the command file's checker function.
    """

    satisfied: bool
    missing: tuple[str, ...]
