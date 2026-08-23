# 10 — Separar contrato de interação do provider Rich

Type: task

**What to build:** a abstração e a implementação concreta de interação deixam de viver no mesmo arquivo. `RichQuestionaryProvider` (implementação Rich/questionary) sai de `interactive/provider.py` para um módulo próprio (`interactive/rich_provider.py`); `provider.py` mantém o contrato `InteractionProvider`, o erro `InteractionCancelledError` e a reexportação do provider concreto.

**Blocked by:** nenhum — pode começar imediatamente.

**Status:** ready-for-agent

- [ ] Contrato e implementação em módulos distintos; `provider.py` reexporta `RichQuestionaryProvider` sem quebrar imports existentes.
- [ ] Nenhum acoplamento a Rich na definição do contrato.
- [ ] `uv run pytest`, `uv run ty check` e `uv run ruff check` verdes (suíte `test_interactive_provider.py` e o `fake_interaction_provider.py` de suporte).

## Contexto (do relatório SRP)

`interactive/provider.py` (459 físicas): `RichQuestionaryProvider` 246 linhas (8 métodos, `ask_multi_choice` 87), `InteractionProvider` 139. O acoplamento concreto a Rich no mesmo arquivo da abstração é o motivo de existir um fake nos testes.