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

**Status:** ready-for-agent

- [ ] Caminho em-memória de `run_measure` usa `measurement_source()` para rows pós-filtro e fieldnames.
- [ ] Dataset ausente → "não ativado"; `Grupo_executor`/`period_column` ausentes → hard-failure em todas as categorias derivadas (como hoje).
- [ ] Avisos `in_values`/`outros` preservados.
- [ ] Emissão de WARN de janela vazia unificada com o caminho single — sem duplicação quando `run` executa split+measure.