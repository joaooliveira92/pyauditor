# 08 — Regra única da aba `INMS_BASE`

**What to build:** a aba `INMS_BASE` do `report.xlsx` (26 colunas) e do `consolidado.xlsx`
(15 colunas) passam a derivar de uma única regra compartilhada de linha de `INMS_BASE`
sobre o mesmo `IndicatorSummary`.

Hoje cada uma tem seu próprio `_inms_base_row` recomputando "Conforme"/"Não conforme",
`round(summary.result_pct, 2)` e `target_value - result_pct` — a numeração contratual
divergente é o mesmo conceito. Após este ticket, mudanças na regra (ex.: critério de
"Conforme") tocam um lugar e os dois workbooks seguem a mesma regra.

**Blocked by:** 07

**Status:** ready-for-agent

- [ ] Existe uma única função de linha `INMS_BASE` consumida pelos renderers de `report` e `consolidate`.
- [ ] As duas abas mantêm seus próprios shapes de coluna (26 vs 15) mas computam "Conforme"/round/`target - result` pela mesma regra.
- [ ] `test_excel_report.py` e `test_excel_consolidate.py` verdes e cobrindo a regra única.