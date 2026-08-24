# 07 — Extrair loop de medição e ROMs combinados do measure

Type: task

**What to build:** o processamento por indicador deixa de ser closure com estado mutável. `_handle_result` e `_hard_fail_todas_categorias` viram funções puras que retornam estado (`outcomes`, `warnings`), sem `nonlocal`; o loop de medição vai para um módulo próprio (`cli/measure/_runner.py`); `write_combined_roms` para outro módulo (`cli/measure/_combined.py`). `run_measure` orquestra chamando os módulos.

**Blocked by:** 06 — resolução de entradas do measure.

**Status:** resolved

- [x] Nenhum `nonlocal` no caminho de medição.
- [x] Comportamento de hard-failure (todas as categorias) e de warnings idêntico ao atual.
- [x] `write_combined_roms` com mesma assinatura para os consumidores de `summary*`.
- [x] `uv run pytest`, `uv run ty check` e `uv run ruff check` verdes.

## Contexto (do relatório SRP)

Parte 2 da divisão do hub CRÍTICO `cli/measure.py`. O maior risco são as closures `nonlocal`; exige primeiro transformá-las em funções puras com retorno de estado, depois mover. Suíte `test_cli_measure.py` (1006 linhas) como rede de aceitação end-to-end.

## Answer

O `cli/measure.py` caiu de 683 → 167 linhas (o `run_measure` virou orquestrador enxuto), dividido em 4 módulos coesos (ticket 07 SRP):

- **`cli/measure_run.py`** (novo) — a classe `MeasureLoop` acumula `outcomes`/`warnings`/`hard_failure` em atributos de instância; as closures `_handle_result`/`_hard_fail_todas_categorias` viraram métodos (sem `nonlocal`). O corpo do `for` original (expansão de categorias em memória + caminho single + warnings `in_values`/`outros`) virou `run_configs`/`_measure_config`/`_measure_categorias`/`_measure_single`. `MeasureLoopResult` devolve o estado final.
- **`cli/measure_contracts.py`** (novo) — `IndicatorOutcome`, `_MeasuredIndicator` e `_sanitize_indicator_id` (antes no `measure.py`), reexportados pelo `measure.py` para preservar a API.
- **`cli/measure_combined.py`** (novo) — `write_combined_roms` (ROMs `both`), mesmo contrato de antes; `measure.py` reexporta.
- **`cli/measure_inputs.py`** — do ticket 06, já existia.

`run_measure` mantém a assinatura pública e o contrato: resolve entradas (ticket 06), roda `MeasureLoop.run_configs(inputs.configs, collect=collect)` e monta o `MeasureResult` (soma warnings de entrada + loop, resumo `measure_done`, status/hard-failure).

Dois testes de `test_cli_measure.py` que patcheavam `pyauditor.cli.measure.measure`/`QualityGateRunner` foram apontados para `pyauditor.cli.measure_run` (onde o símbolo agora vive) — comportamento de patch preservado. `write_combined_roms`/`summary*` consumidores inalterados.

Validação: `uv run pytest` 586 passados, cobertura 89.57% (gate 85% ok); `uv run ty check`, `uv run ruff check`, `uv run ruff format --check` e `uv run bandit` verdes.