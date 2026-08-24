"""Decisão sobre avisos não-fatais de um comando concluído.

Espelha `_decision.py`, mas para avisos: um comando termina `done` com
`result.warnings` não vazio (ex.: linhas não classificadas, `in_values` sem
correspondência) e o chamador decide como a execução segue:

- ``continue``: segue para a próxima etapa, avisos ficam só registrados;
- ``retry``: o usuário ajustou algo fora do processo (ex.: categorias.yaml,
  um CSV de entrada) e quer que a mesma etapa seja despachada de novo antes
  de avançar — diferente do `retry` de falha, aqui o comando já teve
  sucesso, então não há necessidade de tratar dependências de novo;
- ``abort``: para a execução ali, com o estado já persistido `done`
  reaproveitável numa retomada futura.
"""

from __future__ import annotations

from typing import Final, Literal, cast

__all__: Final[tuple[str, ...]] = (
    'WarningDecision',
    'continue_on_warning',
)

type WarningDecision = Literal['continue', 'retry', 'abort']

_WARNING_DECISIONS: Final[frozenset[str]] = frozenset(
    {'continue', 'retry', 'abort'}
)


def continue_on_warning(
    _command: str,
    _orgao: str | None,
    _warnings: tuple[str, ...],
) -> WarningDecision:
    """Default policy: avisos não interrompem a execução (comportamento
    atual, direto)."""
    return 'continue'


def validate_warning_decision(decision: object) -> WarningDecision:
    """Validate a decision returned by the warning callback."""
    if not isinstance(decision, str):
        raise TypeError(
            f'on_warning must return a string decision, received '
            f'{type(decision).__name__}'
        )

    if decision not in _WARNING_DECISIONS:
        raise ValueError(
            f'on_warning returned an unsupported decision: {decision!r}'
        )

    return cast(WarningDecision, decision)
