# 05 — Extrair máquina de decisão de falha do run

Type: task

**What to build:** a lógica de decisão sobre falhas do run deixa de viver no corpo de `execute_run`. `record_failure_and_decide`, `_validate_failure_decision`, `_cascade_skip`, `_abort_on_failure` e `FailureDecision` saem de `orchestration/run.py` para um módulo próprio (`orchestration/_decision.py`); `execute_run` mantém apenas a orquestração.

**Blocked by:** nenhum — pode começar imediatamente.

**Status:** ready-for-agent

- [ ] `execute_run` mantém o mesmo contrato de callbacks (`on_state_change`, `on_failure`) e a mesma ordem de transições de estado.
- [ ] Política retry/skip/isolate/abort preservada exatamente.
- [ ] Sem `nonlocal` de estado de decisão no caminho de execução.
- [ ] `uv run pytest`, `uv run ty check` e `uv run ruff check` verdes (suíte `test_orchestration_run.py` como rede).

## Contexto (do relatório SRP)

`orchestration/run.py` (711 físicas): `execute_run` 304 linhas, `record_failure_and_decide` 62, `_validate_request`/`_cascade_skip` 47 cada. A máquina de estados (resume/skip/cascade) e a decisão de falha são conceitos distintos misturados no mesmo corpo.