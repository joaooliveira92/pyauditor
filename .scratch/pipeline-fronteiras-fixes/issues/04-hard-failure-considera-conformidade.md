# 04 — `hard_failure` passa a considerar `conforms`/`result_pct`

**Origem:** [Engine→orchestration boundary review](../../pipeline-fronteiras-review/issues/02-engine-orchestration-boundary.md)

**What to build:** `hard_failure` (`engine/pipeline.py`) ignora `conforms`/`result_pct` do resultado do indicador — só reflete erros de execução (exceção, config malformada), não uma régua de cálculo sistematicamente não-conforme. Hoje um indicador que roda sem erro mas está estruturalmente quebrado (ex.: sempre 0% de conformidade por um bug de cálculo) não aciona nenhum sinal de falha no resumo do `run`. Ajustar `hard_failure` (ou o resumo consumido por `orchestration`/`cli/measure.py`) para que uma não-conformidade sistemática do indicador também apareça como sinal no resumo — sem transformar toda não-conformidade legítima e pontual em "falha" (o resumo já distingue os dois casos hoje para conformidade pontual; o gap é especificamente sistemático/estrutural).

**Blocked by:** None — can start immediately.

- [ ] Um indicador que roda sem erro mas nunca é conforme aparece sinalizado no resumo do `run`, distinto de "conforme"
- [ ] Não-conformidade pontual/esperada de um indicador continua não sendo tratada como `hard_failure`
- [ ] Teste de regressão cobrindo os dois casos
