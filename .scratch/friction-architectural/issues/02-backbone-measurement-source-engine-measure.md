# 02 — Backbone `measurement_source()`; migrar `engine.measure` (expand)

**What to build:** um novo símbolo de engine `measurement_source(config, data_dir, manifest, periodo, strict) -> SourceBundle` que encapsula o trecho *resolve fonte → valida colunas → lê CSV → filtra período → roda quality gates* e devolve `(config, csv_path, fieldnames, rows, gate_report, accepted_ids, descartes)`.

`engine.pipeline.measure()` passa a ser um thin-orchestrator sobre esse backbone (cálculo + proveniência + resultado). O novo símbolo é **aditivo** — nenhum chamador existente muda, nada quebra. Este é o passo *expand* do wide refactor do pipeline de medição.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] `measurement_source()` existe em `engine` e encapsula resolve→valida→lê→filtra→gates.
- [ ] `SourceBundle` expõe config, csv_path, fieldnames, rows pós-filtro, gate_report, accepted_ids e os descartes (fora-de-período e sem data).
- [ ] `engine.measure` usa o backbone e mantém comportamento idêntico (mesmo `MeasurementResult`, mesmas mensagens de WARN/INFO de janela vazia e descarte) — suíte do engine verde.
- [ ] Backbone coberto por testes próprios (resolve, filtro de período, gates, validação de colunas).