# 05 — Migrar `run_measure` (caminho em-memória) para o backbone

**What to build:** o caminho categorial em-memória de `cli/measure.run_measure` deixa de
reimplementar as etapas iniciais (resolve → read_raw_csv → filtra período) e passa a
usar o backbone `measurement_source()`.

O caminho em-memória precisa do backbone entregando as rows pós-filtro do bruto para
depois segmentar por categoria (filtro `Grupo_executor` em memória, sem materializar
`_split/*`). Deve preservar: o tratamento de dataset ausente como "não ativado", o
`GRUPO_EXECUTOR_COLUMN` ausente e o `period_column` ausente como hard-failure para
todas as categorias derivadas, e os avisos de `in_values`/`outros`.

Aproveitar para reconciliar as divergências de emissão de warnings entre os caminhos:
hoje `engine.measure` emite WARN de janela vazia só no caminho single, o caminho
em-memória não, e o `sintetico` nunca — após este ticket a emissão fica unificada e
documentada no backbone (1x por dataset bruto).

**Blocked by:** 02

**Status:** done

- [x] Caminho em-memória de `run_measure` usa `measurement_source()` para rows pós-filtro e fieldnames.
- [x] Dataset ausente → "não ativado"; `Grupo_executor`/`period_column` ausentes → hard-failure em todas as categorias derivadas (como hoje).
- [x] Avisos `in_values`/`outros` preservados.
- [x] Emissão de WARN de janela vazia unificada com o caminho single — sem duplicação quando `run` executa split+measure.

## Comments

- 2026-08-22 — Implementado. `run_measure` (caminho em-memória)
  chama `measurement_source(..., emit_period_filter_logs=not already_split)`
  (`cli/measure.py`) e usa `bundle.rows`/`fieldnames`/delimiter/encoding e os
  contadores `dropped_out_of_period`/`undated_dropped` do `SourceBundle`. O
  `emit_period_filter_logs` interage com `already_split` para não duplicar o
  WARN/INFO quando `run` executa `split`+`measure` na mesma passada (ticket 11).
  Dataset ausente vira `not_activated=True` ("não ativado"); `Grupo_executor`
  ausente do header → hard-failure em todas as categorias derivadas;
  avisos `in_values`/`outros` emitidos apenas quando `split` ainda não
  cross-checkou os mesmos `real_values` (dedup ticket 11). Suíte completa verde.