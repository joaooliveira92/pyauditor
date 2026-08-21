# 06 — Propagar `force_commands` no resume do fluxo guiado interativo

**Origem:** [Orchestration↔cli/interactive boundary review](../../pipeline-fronteiras-review/issues/03-orchestration-cli-interactive-boundary.md), [Interactive→orchestration boundary review](../../pipeline-fronteiras-review/issues/07-interactive-orchestration-boundary.md)

**What to build:** `cli/run.py` monta `RunRequest` com `force_commands={"report", "consolidate"}`; o fluxo guiado (`interactive/flow.py`) monta `RunRequest` sem `force_commands`. Ao retomar uma sessão guiada interrompida, etapas `report`/`consolidate` já marcadas `done` num estado anterior não são redespachadas — e `orchestration/summary.py` cai em defaults otimistas (`publicable=True`, `glosa_calc=True`) quando não há `Result` desta sessão, então o painel final do modo guiado pode alegar "publicação liberada" sem ter recalculado nada. Fazer o fluxo guiado passar o mesmo `force_commands` que `cli/run.py` já passa.

**Blocked by:** None — can start immediately.

- [ ] Retomar uma sessão guiada interrompida redispara `report`/`consolidate` mesmo se já `done` num estado anterior, igual ao `pyauditor run` direto
- [ ] O painel final do fluxo guiado não alega "publicação liberada" sem ter recalculado nesta sessão
- [ ] Teste de regressão cobrindo o resume do fluxo guiado com estado `done` pré-existente
