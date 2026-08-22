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

**Status:** ready-for-agent

- [ ] Nenhuma etapa duplicada de resolve→lê→filtra→gates fora do backbone (grep confirma zero reimplementações em `sintetico`/`split`/`measure`).
- [ ] `test_measure.py`/`test_cli_measure.py` simulam no boundary do backbone/engine, sem patch módulo-a-módulo das internals de `measure`.
- [ ] Suíte completa do pyauditor verde.