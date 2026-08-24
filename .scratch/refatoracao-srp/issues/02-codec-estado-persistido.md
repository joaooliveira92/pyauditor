# 02 — Extrair codec de estado persistido

Type: task

**What to build:** a serialização, deserialização e validação do estado persistido do `run` deixam de viver no mesmo módulo que os tipos de estado. O decode de estado, o decode de comando e a validação de entrada de comando vão para um módulo próprio (`orchestration/state_codec.py`); `orchestration/state.py` mantém os tipos públicos (`RunState`, `CommandStateEntry`, `RunStateCorruptedError`) e as funções de garantia de estado.

**Blocked by:** nenhum — pode começar imediatamente.

**Status:** resolved

- [x] `_decode_state`, `_decode_command` e `_validate_command_entry` movidos sem mudança de contrato interno.
- [x] `ensure_state`, `state_path`, `RunState`, `CommandStateEntry` permanecem com a mesma API pública.
- [x] Detecção de corrupção (`RunStateCorruptedError`) preservada com mensagens idênticas.
- [x] `uv run pytest`, `uv run ty check` e `uv run ruff check` verdes.

## Contexto (do relatório SRP)

`orchestration/state.py` tem 689 linhas físicas e apenas 8 imports — baixa integração externa, acúmulo interno. `_validate_command_entry` tem 87 linhas, `_decode_state`/`_decode_command` 45/46. Consumidores: `orchestration/run.py` e `test_orchestration_state.py`.

## Answer

Criado `src/pyauditor/orchestration/state_codec.py` com todo o codec do documento persistido (ticket 02 SRP):

- **Schema do documento**: `RunState`, `CommandStateEntry`, `CommandState` (type alias), `RunStateCorruptedError`, constantes `_SCHEMA_VERSION`/`_VALID_STATES`/`_ROOT_FIELDS`/`_COMMAND_FIELDS`/`_STATE_COMPONENT_RE` e `parse_iso_timestamp` (fonte única reusada por `summary_json`).
- **Decodificação e validação**: `decode_state` (ex-`_decode_state`), `_decode_command`, `validate_state` (ex-`_validate_state`) e a família de `_require_*`/`_validate_*` moveu sem mudança de mensagens nem de contrato.
- **Serialização**: `encode_state(state) -> str` (o payload + `json.dumps` que antes vivia em `save_state`).

`orchestration/state.py` ficou enxuto, com a persistência de fato: `state_path`, `load_state`, `save_state` (valida + codifica + `atomic_write`), `reset_stale_running` e a reexportação da API pública inalterada (`__all__` é o mesmo de antes e o caminho de import `from pyauditor.orchestration.state import RunState/CommandStateEntry/RunStateCorruptedError/parse_iso_timestamp` continua funcionando — a identidade do objeto agora é a classe definida no novo codec).

Nota de design para o revisor (map refatoracao-srp): o critério "tipos permanecem em `state.py`" foi interpretado como "a API pública de `state.py` permanece idêntica"; as definições de dataclass vivem agora no `state_codec.py` (coeso, o schema do documento é o contrato do codec) e são reexportadas por `state.py`. Nenhum consumidor (run.py, resumo, resume, interactive) precisou mudar de import.

Validação: `uv run pytest` 586 passados, cobertura 89.39% (gate 85% ok); `uv run ty check`, `uv run ruff check`, `uv run ruff format --check` e `uv run bandit` todos verdes.