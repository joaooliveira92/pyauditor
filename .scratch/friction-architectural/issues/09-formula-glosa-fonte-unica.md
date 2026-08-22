# 09 — Fórmula de glosa em fonte única

**What to build:** `excel/consolidate.py` deixa de reescrever a fórmula de glosa e passa
a importar as constantes e a aritmética de `excel/glosas.py`.

Hoje `consolidate.py` reescreve `pontos * 0.001` em 4 linhas e define `LIMITE_PCT = 30.0`
própria, enquanto `glosas.py` guarda `POINTS_TO_PERCENT = 0.001` e `CAP_PCT = 30` com
`compute_glosa`. Além disso, `build_calculo` recalcula o `MIN(pontos×0.001, 30%)/100 ×
bruto` em células — a mesma aritmética que `compute_glosa` acabou de computar. Se o TR
mudar o teto ou o fator, hoje são 4 pontos de edição; após o ticket, um só.

**Blocked by:** None — can start immediately.

**Status:** done

- [x] `consolidate.py` usa `POINTS_TO_PERCENT`/`CAP_PCT`/`compute_glosa` de `glosas.py`; `LIMITE_PCT` local removida.
- [x] Aritmética das células de `build_calculo` deriva da mesma fonte (sem `0.001`/`30` literais fora de `glosas.py`).
- [x] Nenhum valor mágico de teto/fator de glosa duplicado no código (grep confirma).
- [x] `test_excel_consolidate.py` e `test_excel_glosas.py` verdes.

## Comments

- 2026-08-22 — Implementado. `consolidate.py` importa `POINTS_TO_PERCENT`/`CAP_PCT` de
  `glosas.py` e remove `LIMITE_PCT` local. O `0.001`/`30.0` das células de
  `CALCULO_PAGAMENTO` agora deriva de `_glosa_bruto` (wrapper sobre
  `compute_glosa`, fonte única). Grep confirma zero literais de fator/teto fora de
  `glosas.py`. Testes: 32 passed (`test_excel_consolidate` + `test_glosas`).