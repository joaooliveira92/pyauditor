# 04 — Integrar `split` em `run`/máquina de estado

**What to build:** `split` (ticket 03) passa a ser disparado automaticamente por
`pyauditor run <competência>`, entre `bootstrap` e `measure`, com a mesma transacionalidade por
órgão dos demais comandos (`docs/spec/inms-pipeline.md` §14.3, item "Nome do comando e posição em
`run`"). Uma falha em `split` de um órgão bloqueia só o `measure` (e downstream) daquele órgão — não
o `bootstrap`/`split`/`measure` do outro órgão, mesmo padrão já implementado para
`bootstrap`→`measure`→`report` em `src/pyauditor/orchestration/run.py`.

Mudanças mecânicas em `orchestration/run.py`: `_PHASE_ORDER` e `_ALL_COMMANDS` ganham `"split"`
entre `"bootstrap"` e `"measure"`; `_dispatch` ganha o case; `dependency_missing`/`CHECKERS`
(`src/pyauditor/cli/dependencies.py`) ganham `check_split_ready`. `_plan`, `_downstream`,
`_cascade_skip` já são genéricos por fase — não deveriam precisar de mudança de lógica, só do dado
novo em `_PHASE_ORDER`.

**Blocked by:** 03

**Status:** ready-for-agent

- [ ] `pyauditor run <competência>` executa `bootstrap` → `split` → `measure` → `report` →
      `consolidate` na ordem certa, por órgão
- [ ] `split` registra estado (`pending`/`running`/`done`/`error`/`skipped`) no
      `RunState` igual aos demais comandos, incluindo resume (`--force` e retomada após falha)
- [ ] Uma falha em `split` do MinC isola só `measure`/`report` do MinC (via `isolate_on_failure`) e
      não impede `bootstrap`/`split`/`measure` do MTur de rodar
- [ ] `pyauditor split` continua funcionando como comando standalone (ticket 03), sem regressão
- [ ] Teste de integração cobrindo um `execute_run` completo com `split` no meio, incluindo o caso de
      falha isolada por órgão
- [ ] `uv run mypy --strict src` e `uv run pytest` verdes
