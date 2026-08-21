# 09 — Cross-checar modo `in_values` de `categorias.yaml` contra os valores reais do CSV

**Origem:** [Categoria/split boundary review](../../pipeline-fronteiras-review/issues/08-categoria-split-boundary.md)

**What to build:** `categoria_filter.py` resolve `catch_all_contains` contra os valores reais do CSV e avisa quando algo sobra (caminho `outros`), mas o modo `in_values` — o mais explícito, listando literais esperados — nunca é cruzado com os valores reais. Um typo ou renomeação de fila/valor no CSV de origem produz silenciosamente uma medição de "categoria sem linhas", indistinguível de zero atividade real, sem warning. Adicionar a mesma checagem cruzada que `catch_all_contains` já tem: se nenhum valor de `in_values` aparece no CSV real, emitir warning nomeando os valores configurados que não bateram com nada.

**Blocked by:** None — can start immediately.

- [ ] Um `in_values` cujo(s) literal(is) não aparece(m) em nenhuma linha do CSV real emite warning nomeando os valores configurados sem correspondência
- [ ] Teste de regressão cobrindo `in_values` com valor inexistente no CSV
