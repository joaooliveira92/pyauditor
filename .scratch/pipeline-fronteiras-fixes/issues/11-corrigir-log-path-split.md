# 11 — Corrigir o path de log do `split`

**Origem:** [Cli dispatch boundary review](../../pipeline-fronteiras-review/issues/06-cli-dispatch-boundary.md)

**What to build:** `_dispatch_split` (`cli/main.py`) usa `data_dir/<orgao>/<competencia>` como convenção do path de log — a mesma convenção de saída (ROM) usada por `measure` — mas os artefatos reais do `split` ficam em `data_dir/<orgao>/<ano>/<mes>/_split/...`. Com `--orgao both`, o log cai numa pasta `both/` órfã, já que `split` não tem um passo "combinado" como `measure`. Corrigir o path de log do `split` para refletir onde ele de fato escreve.

**Blocked by:** None — can start immediately.

- [ ] O log do `split` fica no mesmo diretório (ou um caminho previsível a partir dele) de onde os artefatos do `split` são gravados
- [ ] `pyauditor split --orgao both` não produz uma pasta de log órfã
