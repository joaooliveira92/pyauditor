# 02 — Extrair codec de estado persistido

Type: task

**What to build:** a serialização, deserialização e validação do estado persistido do `run` deixam de viver no mesmo módulo que os tipos de estado. O decode de estado, o decode de comando e a validação de entrada de comando vão para um módulo próprio (`orchestration/state_codec.py`); `orchestration/state.py` mantém os tipos públicos (`RunState`, `CommandStateEntry`, `RunStateCorruptedError`) e as funções de garantia de estado.

**Blocked by:** nenhum — pode começar imediatamente.

**Status:** ready-for-agent

- [ ] `_decode_state`, `_decode_command` e `_validate_command_entry` movidos sem mudança de contrato interno.
- [ ] `ensure_state`, `state_path`, `RunState`, `CommandStateEntry` permanecem com a mesma API pública.
- [ ] Detecção de corrupção (`RunStateCorruptedError`) preservada com mensagens idênticas.
- [ ] `uv run pytest`, `uv run ty check` e `uv run ruff check` verdes.

## Contexto (do relatório SRP)

`orchestration/state.py` tem 689 linhas físicas e apenas 8 imports — baixa integração externa, acúmulo interno. `_validate_command_entry` tem 87 linhas, `_decode_state`/`_decode_command` 45/46. Consumidores: `orchestration/run.py` e `test_orchestration_state.py`.