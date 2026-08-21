# 02 — Validar nomes de coluna configurados contra o header real do CSV, uma vez, na borda do engine

**Origem:** [Config→engine boundary review](../../pipeline-fronteiras-review/issues/01-config-engine-boundary.md), [Engine→orchestration boundary review](../../pipeline-fronteiras-review/issues/02-engine-orchestration-boundary.md)

**What to build:** Nenhum nome de coluna declarado em YAML (`Filter.column`, `id_column`, `*_column` de qualquer strategy) é validado contra o cabeçalho real do CSV antes do cálculo. Hoje isso se manifesta de formas diferentes conforme o ponto de leitura: `_filters.py` resolve para `""` e zera silenciosamente (`ColumnEquals`/`ColumnIn`) ou casa tudo (`ColumnNotEquals`); `external_catalog_sum.py` descarta ocorrências sem log; `quality_gates.py` estoura `KeyError` cru. Adicionalmente, um typo na chave `indicator:` do próprio YAML (ex. `indicador:`) faz `pipeline.py` pular o arquivo inteiro como "não é config de indicador", sem aviso. Adicionar uma validação única, na borda onde o CSV é carregado e a config é lida (antes de qualquer strategy rodar), que confere todo nome de coluna referenciado no YAML contra o header real do CSV e levanta um erro acionável nomeando o arquivo de config e a coluna ausente/typo — substituindo os `.get(col, "")` silenciosos e os `KeyError` crus.

**Blocked by:** None — can start immediately.

- [ ] Uma coluna referenciada em qualquer campo `*_column`/`Filter.column` do YAML que não existe no header do CSV falha com erro nomeando o arquivo de config e a coluna, antes de qualquer strategy calcular
- [ ] Uma config YAML com a chave `indicator:` ausente/typada errado falha com erro acionável, em vez de ser silenciosamente pulada
- [ ] Testes de regressão cobrindo os três caminhos hoje silenciosos (`_filters.py`, `external_catalog_sum.py`, `pipeline.py`'s skip de config malformada)
