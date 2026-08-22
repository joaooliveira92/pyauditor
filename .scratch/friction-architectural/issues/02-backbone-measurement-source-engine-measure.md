# 02 — Backbone `measurement_source()`; migrar `engine.measure` (expand)

**What to build:** um novo símbolo de engine `measurement_source(config, data_dir, manifest, periodo, strict) -> SourceBundle` que encapsula o trecho *resolve fonte → valida colunas → lê CSV → filtra período → roda quality gates* e devolve `(config, csv_path, fieldnames, rows, gate_report, accepted_ids, descartes)`.

`engine.pipeline.measure()` passa a ser um thin-orchestrator sobre esse backbone (cálculo + proveniência + resultado). O novo símbolo é **aditivo** — nenhum chamador existente muda, nada quebra. Este é o passo *expand* do wide refactor do pipeline de medição.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [x] `measurement_source()` existe em `engine` e encapsula resolve→valida→lê→filtra→gates.
- [x] `SourceBundle` expõe config, csv_path, fieldnames, rows pós-filtro, gate_report, accepted_ids e os descartes (fora-de-período e sem data).
- [x] `engine.measure` usa o backbone e mantém comportamento idêntico (mesmo `MeasurementResult`, mesmas mensagens de WARN/INFO de janela vazia e descarte) — suíte do engine verde.
- [x] Backbone coberto por testes próprios (resolve, filtro de período, gates, validação de colunas).

## Comments

- 2026-08-22 — Implementado. `measurement_source()`/`SourceBundle` em
  `engine/pipeline.py`; `measure()` virou thin-orchestrator. A leitura usa
  `categoria_filter.read_raw_csv` (não `load_rows`) para herdar a
  normalização do alias `"Grupo executor"` -> `"Grupo_executor"` que
  `split`/`sintetico`/`cli.measure` já aplicavam cada um a seu jeito —
  necessário para as migrações 03-05 não mudarem de comportamento.
  `emit_empty_window_warning` (default `True`) existe desde já para o
  ticket 05 poder suprimir o WARN duplicado quando `run` já rodou `split`
  na mesma passada. Testes: `tests/test_measurement_source.py`. Suíte
  completa: mesmos 66 failures pré-existentes antes/depois (confirmado via
  `git stash`), nenhuma regressão.