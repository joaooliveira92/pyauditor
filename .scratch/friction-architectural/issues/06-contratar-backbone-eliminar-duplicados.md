# 06 — Contratar o backbone; eliminar duplicados e dar boundary ao teste (contract)

**What to build:** com os 4 chamadores (02–05) sobre o backbone, remover as etapas
duplicadas que sobraram e contratar a API:

- qualquer código morto/duplicado de resolve→lê→filtra→gates que não passe mais pelo
  backbone é removido; os 4 pontos viram thin-orchestrators que só orquestram e
  formatam saída;
- o caminho em-memória de `run_measure` ganha um boundary de engine real para fakes:
  `test_measure.py`/`test_cli_measure.py` deixam de patchar módulo-por-módulo
  (`discover_config_files`, `.measure`, `.render_rom`, `.summarize`) e passam a simular
  no backbone/na saída observável — mesmo sintoma do achado #10.

Este é o passo *contract* do wide refactor do pipeline de medição. A suíte completa
deve ficar verde.

**Blocked by:** 03, 04, 05

**Status:** done

- [x] Nenhuma etapa duplicada de resolve→lê→filtra→gates fora do backbone (grep confirma zero reimplementações em `sintetico`/`split`/`measure`).
- [x] `test_measure.py`/`test_cli_measure.py` simulam no boundary do backbone/engine, sem patch módulo-a-módulo das internals de `measure`.
- [x] Suíte completa do pyauditor verde.

## Comments

- 2026-08-22 — Implementado. (a) Grep confirma que os 4 chamadores
  (`engine.pipeline.measure`, `excel/sintetico`, `cli/split`, `cli/measure`)
  roteiam todo resolve→lê→filtra→gates pelo backbone `measurement_source()`;
  nenhuma etapa duplicada fora dele. (b) `tests/test_measure.py` reescrito para
  fixture real (config YAML + CSV no tmp_path + `run_measure` real) em vez de
  patchar `discover_config_files`/`.measure`/`.render_rom`/`.summarize`
  módulo-a-módulo — os únicos `patch` restantes são `Path.mkdir`/`Path.write_text`
  (boundary de I/O observável). `test_cli_measure.py` continua sem patches de
  internals (já usava rotas reais). Suíte alvo (59) verde.