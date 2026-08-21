# 01 — Corrigir glosa em dobro na segmentação por Categoria

**Origem:** [Categoria/split boundary review](../../pipeline-fronteiras-review/issues/08-categoria-split-boundary.md)

**What to build:** `split` grava a config derivada por categoria no mesmo `config_dir` da config base (`inms-<n>.yaml`). `measure` descobre ambas via glob e gera um ROM/summary por config, todas com o mesmo `contractual_id` — só o `id` interno muda. `excel/report.py` soma `penalty_points` de todos os summaries sem deduplicar por `contractual_id`, contando a glosa financeira N+1 vezes em vez de N para todo INMS segmentado por Categoria. Corrigir para que a soma de glosa de um INMS segmentado seja idêntica à soma que existiria sem segmentação — a config base não deve contribuir penalidade quando já existem configs derivadas por categoria para o mesmo INMS, e nenhuma linha do CSV deve ser contada por mais de uma categoria.

**Blocked by:** None — can start immediately.

- [ ] `measure`/`report` não computam penalidade da config base de um INMS quando existem configs derivadas por Categoria para o mesmo `contractual_id`
- [ ] Teste de regressão: um INMS segmentado em N categorias produz a mesma glosa total que o mesmo INMS sem segmentação, para o mesmo CSV de entrada
- [ ] Nenhuma linha do CSV é contada em mais de uma categoria (achado correlato do ticket de origem: sobreposição entre categorias não é validada)
