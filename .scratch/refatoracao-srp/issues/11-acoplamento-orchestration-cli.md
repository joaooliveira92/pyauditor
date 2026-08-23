# 11 — Quebrar acoplamento orchestration → cli

Type: task

**What to build:** a camada de orquestração deixa de depender das funções e dataclasses de comando concretas de `cli/`. As dataclasses de resultado (`MeasureResult`, `SplitResult`, `BootstrapResult`, `ReportResult`, `ConsolidateResult`) mudam para um módulo de contratos neutro (ex.: `pyauditor/commands/contracts.py`); `orchestration/command_dispatch.py`, `summary.py` e `summary_json.py` passam a depender do contrato, não do comando. Sequência expand–contract: manter os imports antigos funcionando durante a migração e removê-los só quando nenhum chamador restar, em lotes por pacote mantendo CI verde lote a lote.

**Blocked by:** 06, 07, 08 — resolução de entradas do measure, loop de medição, derivação do split (mesmos arquivos; evita conflito de merge).

**Status:** ready-for-agent

- [ ] Nenhum módulo de `orchestration/` importa função de comando concreta de `cli/`.
- [ ] Expand–contract executado em lotes por pacote; CI verde em cada lote.
- [ ] Nenhum ciclo de import introduzido.
- [ ] Sem `dict[str, Any]` nos contratos — `ty` strict continua valendo.
- [ ] `uv run pytest`, `uv run ty check` e `uv run ruff check` verdes.

## Contexto (do relatório SRP)

Risco arquitetural nº 1: `orchestration/command_dispatch.py`, `summary.py` e `summary_json.py` importam `run_measure`, `run_bootstrap` e as dataclasses de resultado de dentro de `cli/`. A camada de orquestração depende da camada de apresentação de comando — o oposto da pirâmide. `summary.py` tem 21 imports, 5 deles de `cli`.