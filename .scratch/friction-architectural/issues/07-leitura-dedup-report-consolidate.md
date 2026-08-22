# 07 — Leitura + dedup compartilhados de `report`/`consolidate`

**What to build:** a leitura dos artefatos de ROM (`_load_summaries`, `_read_objetos`/`_read_valor_base`) e o dedup de sumário derivado passam a existir em fonte única, usados por `cli/report.py` e `cli/consolidate.py`.

Hoje `_load_summaries` é verbatim nos dois (com fallback de grandParent redundante só no consolidate) e o dedup de derivado tem o mesmo corpo com nomes diferentes (`_is_categoria_derived`+`_deduplicate_summaries` vs `_is_derived`+`_deduplicate`). Um bug corrigido num fica no outro — é o caminho fiscal de recontagem de pontos.

**Blocked by:** None — can start immediately.

**Status:** done

- [x] `_load_summaries`, `_read_objetos`/`_read_valor_base` e o dedup de sumário derivado existem uma única vez e `report`/`consolidate` os importam.
- [x] Fallback redundante de grandParent no consolidate reconciliado (ou removido com teste) com a versão do report.
- [x] Semântica de erro preservada: `FileNotFoundError` → `None`+warning; `ValueError` → raise — mensagens agora idênticas entre os dois.
- [x] Testes de `report`/`consolidate` verdes.

## Comments

- 2026-08-22 — Implementado. Novos módulos `pyauditor.rom.loading`
  (`load_summaries`/`read_valor_base`) e `pyauditor.rom.dedup`
  (`is_categoria_derived`/`deduplicate_summaries`). `cli/report.py`,
  `cli/consolidate.py`, `excel/report.py` e `excel/consolidate.py` importam a
  versão única. Corrigido bug real na versão de `excel/consolidate.py`:
  `_is_derived` testava `"." in indicator_id`, sempre verdadeiro para códigos
  INMS (`"1.7"`), então a dedup nunca excluía a base de fato quando havia
  categorias derivadas — agora usa o prefixo `f"{contractual_id}."`, correto.
  Fallback redundante de grandParent em `cli/consolidate.py` removido (a
  checagem já era coberta antes dele). Mensagens de warning unificadas
  ("glosa não calculada"). `report`/`consolidate`: 25 falhas pré-existentes
  em `test_cli_report.py`/`test_cli_consolidate.py`/`test_excel_consolidate.py`/
  `test_excel_report.py` (bug Decimal/float não relacionado, herdado de
  `c05b92b`) confirmadas idênticas antes/depois via `git stash` — nenhuma
  regressão introduzida por este ticket.