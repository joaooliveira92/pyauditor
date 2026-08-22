# 07 — Leitura + dedup compartilhados de `report`/`consolidate`

**What to build:** a leitura dos artefatos de ROM (`_load_summaries`, `_read_objetos`/`_read_valor_base`) e o dedup de sumário derivado passam a existir em fonte única, usados por `cli/report.py` e `cli/consolidate.py`.

Hoje `_load_summaries` é verbatim nos dois (com fallback de grandParent redundante só no consolidate) e o dedup de derivado tem o mesmo corpo com nomes diferentes (`_is_categoria_derived`+`_deduplicate_summaries` vs `_is_derived`+`_deduplicate`). Um bug corrigido num fica no outro — é o caminho fiscal de recontagem de pontos.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] `_load_summaries`, `_read_objetos`/`_read_valor_base` e o dedup de sumário derivado existem uma única vez e `report`/`consolidate` os importam.
- [ ] Fallback redundante de grandParent no consolidate reconciliado (ou removido com teste) com a versão do report.
- [ ] Semântica de erro preservada: `FileNotFoundError` → `None`+warning; `ValueError` → raise — mensagens agora idênticas entre os dois.
- [ ] Testes de `report`/`consolidate` verdes.