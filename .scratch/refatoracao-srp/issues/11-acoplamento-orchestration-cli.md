# 11 — Quebrar acoplamento orchestration → cli

Type: task

**What to build:** a camada de orquestração deixa de depender das funções e dataclasses de comando concretas de `cli/`. As dataclasses de resultado (`MeasureResult`, `SplitResult`, `BootstrapResult`, `ReportResult`, `ConsolidateResult`) mudam para um módulo de contratos neutro (ex.: `pyauditor/commands/contracts.py`); `orchestration/command_dispatch.py`, `summary.py` e `summary_json.py` passam a depender do contrato, não do comando. Sequência expand–contract: manter os imports antigos funcionando durante a migração e removê-los só quando nenhum chamador restar, em lotes por pacote mantendo CI verde lote a lote.

**Blocked by:** 06, 07, 08 — resolução de entradas do measure, loop de medição, derivação do split (mesmos arquivos; evita conflito de merge).

**Status:** resolved

- [x] Nenhum módulo de `orchestration/` importa função de comando concreta de `cli/`.
- [x] Expand–contract executado em lotes por pacote; CI verde em cada lote.
- [x] Nenhum ciclo de import introduzido.
- [x] Sem `dict[str, Any]` nos contratos — `ty` strict continua valendo.
- [x] `uv run pytest`, `uv run ty check` e `uv run ruff check` verdes.

## Contexto (do relatório SRP)

Risco arquitetural nº 1: `orchestration/command_dispatch.py`, `summary.py` e `summary_json.py` importam `run_measure`, `run_bootstrap` e as dataclasses de resultado de dentro de `cli/`. A camada de orquestração depende da camada de apresentação de comando — o oposto da pirâmide. `summary.py` tem 21 imports, 5 deles de `cli`.

## Answer

Criado `src/pyauditor/commands/` (pacote neutro) com `contracts.py` — as dataclasses de resultado `BootstrapResult`, `MeasureResult`, `SplitResult` (+ `SplitCategoriaOutcome`), `ReportResult`, `ConsolidateResult` e a derivação de código de saída `exit_code_for_results`, mais reexports de `exit_code_name`/`is_production_command`. Sem `dict[str, Any]`: `indicator` do `MeasureResult` referencia `IndicatorOutcome` (de `cli.measure_contracts`, sem ciclo — o contrato não importa `cli.measure`).

Fases (expand–contract):
1. **Expand**: cada `cli/<comando>.py` passou a reexportar a própria dataclass do contrato (`BootstrapResult = contracts.BootstrapResult` etc.) — API pública de `cli.*` inalterada. `cli/results.exit_code_for_results` foi **removida** e `cli/main.py` passou a importá-la de `commands.contracts` (fonte única).
2. **Migrate**: `orchestration/summary.py` e `orchestration/summary_json.py` deixaram de importar `*Result`/`exit_code_*`/`is_production_command` de `cli/*` e passaram a importar de `pyauditor.commands.contracts`.
3. **Contract**: verificado `grep` — nenhum `orchestration/*` importa `Result`/`exit_code`/`is_production` de `cli`. `command_dispatch` segue importando `run_*` concretos (é o dispatcher, não contratos) — fora do escopo declarado do 11.

Sem ciclo de import (verificado por import end-to-end); `ty` strict verde o tempo todo.

Validação: `uv run pytest` 586 passados, cobertura 89.58% (gate 85% ok); `uv run ty check`, `uv run ruff check`, `uv run ruff format --check` e `uv run bandit` verdes.