# 05 — Extrair máquina de decisão de falha do run

Type: task

**What to build:** a lógica de decisão sobre falhas do run deixa de viver no corpo de `execute_run`. `record_failure_and_decide`, `_validate_failure_decision`, `_cascade_skip`, `_abort_on_failure` e `FailureDecision` saem de `orchestration/run.py` para um módulo próprio (`orchestration/_decision.py`); `execute_run` mantém apenas a orquestração.

**Blocked by:** nenhum — pode começar imediatamente.

**Status:** resolved

- [x] `execute_run` mantém o mesmo contrato de callbacks (`on_state_change`, `on_failure`) e a mesma ordem de transições de estado.
- [x] Política retry/skip/isolate/abort preservada exatamente.
- [x] Sem `nonlocal` de estado de decisão no caminho de execução.
- [x] `uv run pytest`, `uv run ty check` e `uv run ruff check` verdes (suíte `test_orchestration_run.py` como rede).

## Contexto (do relatório SRP)

`orchestration/run.py` (711 físicas): `execute_run` 304 linhas, `record_failure_and_decide` 62, `_validate_request`/`_cascade_skip` 47 cada. A máquina de estados (resume/skip/cascade) e a decisão de falha são conceitos distintos misturados no mesmo corpo.

## Answer

A máquina de decisão saiu de `orchestration/run.py` em dois módulos coesos:

- **`orchestration/_decision.py`** (novo) — `FailureDecision`, `_FAILURE_DECISIONS`, `isolate_on_failure`, `_abort_on_failure`, `_validate_failure_decision`, `_cascade_skip` e `handle_failure`. A closure `record_failure_and_decide` (que usava `nonlocal state`) virou `handle_failure(state, *, command, orgao, error_message, started_at, finished_at, plan, path, on_state_change, on_failure, skipped_steps) -> tuple[RunState, FailureDecision]` — função pura que persiste a entrada `error`, decide via `on_failure`, aplica `skip`/`isolate` (incl. cascade) e devolve o estado atualizado, sem `nonlocal`.
- **`orchestration/_flow_helpers.py`** (novo) — `now`, `sanitize_error_message`, `find_entry`, `upsert`, `notify_state_change`, `_MAX_ERROR_MESSAGE_LENGTH`; compartilhados entre `run` e `_decision` para evitar o ciclo de import (o `_cascade_skip` depende deles).

`run.py`: `execute_run` agora orquestra, chamando `handle_failure` nos três pontos de falha (dependência, exceção de dispatch, resultado não-done) com `state, decision = handle_failure(...)` — o `nonlocal` sumiu. Defaults `_noop_state_change`/`_abort_on_failure` e reexport da API pública (`__all__` inalterado: `FailureDecision`, `RunRequest`, `RunResult`, `dependency_missing`, `execute_run`, `isolate_on_failure`) preservados.

Sem mudança de comportamento — mesma ordem de transições, mesmos fallbacks de mensagem persistida (o `except` segue sanitizando `str(exc)` com o fallback `"<Tipo> durante <command>"` antes de passar ao `handle_failure`). Suíte `test_orchestration_run.py` (19 testes de política/retomada) verde sem alterações.

Validação: `uv run pytest` 586 passados, cobertura 89.43% (gate 85% ok); `uv run ty check`, `uv run ruff check`, `uv run ruff format --check` e `uv run bandit` verdes.