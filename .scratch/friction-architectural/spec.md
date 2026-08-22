# Fricção arquitetural — pyauditor

## Contexto

Auditoria de fricções arquiteturais no pipeline do pyauditor (contrato 40/2022,
MinC/MTur). O relatório identificou 10 classes de duplicação/seam vazado. O achado
mais forte é a reimplementação do pipeline de medição em 4 módulos
(`engine.pipeline.measure`, `excel/sintetico.write_sintetico_workbook`,
`cli/split.run_split`, `cli/measure.run_measure`); o segundo é a resolução
divergente de `configs/_shared` + manifest entre `cli/main.py` e
`orchestration/run.py`.

O backbone de medição é um **wide refactor** (blast radius que atravessa engine,
excel e cli) — sequenciado como **expand–contract** (tickets 02–06). Os demais
achados são dedups pontuais (tickets 07–12).

## Tickets

- **01** — Resolução `configs/_shared` + manifest em fonte única (achado 6)
- **02** — Backbone `measurement_source()`; migrar `engine.measure` (expand, achado 1)
- **03** — Migrar `write_sintetico_workbook` para o backbone (achado 1)
- **04** — Migrar `run_split` para o backbone (achado 1)
- **05** — Migrar `run_measure` (caminho em-memória) para o backbone (achado 1)
- **06** — Contratar o backbone; eliminar duplicados e dar boundary ao teste (contract, achado 10)
- **07** — Leitura + dedup compartilhados de `report`/`consolidate` (achados 2, 5-primeiro)
- **08** — Regra única da aba `INMS_BASE` (achado 3)
- **09** — Fórmula de glosa em fonte única (achado 5-segundo)
- **10** — `is_final_month` chega ao consolidate (achado 9)
- **11** — Dono único categoria→nível + dedup de avisos `in_values`/`outros` (achado 8)
- **12** — Dedup do dispatch per-órgão `main`/`run` (achado 7)

## Ordem

Bloqueadores primeiro; qualquer ticket sem blockers pode começar. A fronteira
inicial é 01, 02, 07, 09, 10 (sem blockers).