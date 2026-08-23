# 10 — Separar contrato de interação do provider Rich

Type: task

**What to build:** a abstração e a implementação concreta de interação deixam de viver no mesmo arquivo. `RichQuestionaryProvider` (implementação Rich/questionary) sai de `interactive/provider.py` para um módulo próprio (`interactive/rich_provider.py`); `provider.py` mantém o contrato `InteractionProvider`, o erro `InteractionCancelledError` e a reexportação do provider concreto.

**Blocked by:** nenhum — pode começar imediatamente.

**Status:** resolved

- [x] Contrato e implementação em módulos distintos; `provider.py` reexporta `RichQuestionaryProvider` sem quebrar imports existentes.
- [x] Nenhum acoplamento a Rich na definição do contrato.
- [x] `uv run pytest`, `uv run ty check` e `uv run ruff check` verdes (suíte `test_interactive_provider.py` e o `fake_interaction_provider.py` de suporte).

## Contexto (do relatório SRP)

`interactive/provider.py` (459 físicas): `RichQuestionaryProvider` 246 linhas (8 métodos, `ask_multi_choice` 87), `InteractionProvider` 139. O acoplamento concreto a Rich no mesmo arquivo da abstração é o motivo de existir um fake nos testes.

## Answer

`interactive/` agora tem três módulos coesos (ticket 10 SRP):

- **`interactive/_contract.py`** (novo) — `InteractionProvider` (Protocol), `InteractionCancelledError`, `MultiChoiceOption`, `TextValidator`. Sem import de Rich/Questionary.
- **`interactive/rich_provider.py`** (novo) — `RichQuestionaryProvider` (incl. a montagem de `questionary.Choice` e as validações de opção), que importa o contrato.
- **`interactive/provider.py`** — reexporta o contrato + a implementação, `__all__` inalterado (API pública preservada; consumidores `flow.py`, `cli/main.py` e `tests/support/fake_interaction_provider.py` seguem importando de `provider`).

O 4 testes de `test_interactive_provider.py` que patcheavam `pyauditor.interactive.provider.questionary` foram apontados para `pyauditor.interactive.rich_provider.questionary` (onde o símbolo agora vive). Sem mudança de comportamento.

Validação: `uv run pytest` 586 passados, cobertura 89.66% (gate 85% ok); `uv run ty check`, `uv run ruff check`, `uv run ruff format --check` e `uv run bandit` verdes.