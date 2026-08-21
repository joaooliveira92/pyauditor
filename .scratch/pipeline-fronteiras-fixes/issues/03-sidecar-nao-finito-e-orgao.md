# 03 — Bloquear NaN/Infinity e cross-checar `orgao` no sidecar JSON

**Origem:** [Rom→excel boundary review](../../pipeline-fronteiras-review/issues/04-rom-excel-boundary.md), [Engine→orchestration boundary review](../../pipeline-fronteiras-review/issues/02-engine-orchestration-boundary.md)

**What to build:** `IndicatorSummary._require_numeric` (`rom/summary.py`) só checa `isinstance(..., int | float)`, não finitude — e `json.loads` aceita `NaN`/`Infinity` por padrão. Um sidecar com `"result_pct": NaN` passa ileso e corrompe células/totais no Excel sem exceção em nenhum ponto da cadeia. Separadamente, `orgao` do sidecar é lido como `str` livre e nunca cross-checado contra o diretório de origem (`data_dir/<orgao>/...`); um sidecar mal-rotulado (cópia/edição manual) some silenciosamente de uma linha inteira na consolidação MinC+MTur em vez de errar. Corrigir os dois: `_require_numeric` rejeita não-finitos com erro nomeando o campo e o arquivo; a leitura do sidecar confere `orgao` contra o diretório de onde foi lido e falha se divergir.

**Blocked by:** None — can start immediately.

- [ ] Um sidecar com `NaN`/`Infinity` em qualquer campo numérico falha ao carregar, nomeando o campo e o arquivo
- [ ] Um sidecar cujo `orgao` interno diverge do diretório de origem falha ao carregar, nomeando o caminho e o valor divergente
- [ ] Testes de regressão para os dois casos
