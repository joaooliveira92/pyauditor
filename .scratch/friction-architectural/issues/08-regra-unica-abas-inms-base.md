# 08 — Regra única da aba `INMS_BASE`

**What to build:** a aba `INMS_BASE` do `report.xlsx` (26 colunas) e do `consolidado.xlsx`
(15 colunas) passam a derivar de uma única regra compartilhada de linha de `INMS_BASE`
sobre o mesmo `IndicatorSummary`.

Hoje cada uma tem seu próprio `_inms_base_row` recomputando "Conforme"/"Não conforme",
`round(summary.result_pct, 2)` e `target_value - result_pct` — a numeração contratual
divergente é o mesmo conceito. Após este ticket, mudanças na regra (ex.: critério de
"Conforme") tocam um lugar e os dois workbooks seguem a mesma regra.

**Blocked by:** 07

**Status:** done

- [x] Existe uma única função de linha `INMS_BASE` consumida pelos renderers de `report` e `consolidate`.
- [x] As duas abas mantêm seus próprios shapes de coluna (26 vs 15) mas computam "Conforme"/round/"target - result" pela mesma regra.
- [x] `test_excel_report.py` e `test_excel_consolidate.py` verdes e cobrindo a regra única.

## Comments

- 2026-08-22 — Implementado. Novo módulo `pyauditor/excel/inms_base.py` com a regra única
  `inms_base_fields(summary, competencia, *, grupo_operacional)` (campos
  "Conforme"/round/"meta-diferença" com respeito ao sentido do operador via
  `compliance_margin`) e `compliance_margin` (movido de `excel/report.py`).
  `report._inms_base_row` (26 col) e `consolidate._inms_base_row` (15 col) agora
  derivam da mesma regra e só reposicionam os campos no próprio shape —
  eliminada a divergência de sinal (`target - result` cego no consolidate vs
  `_compliance_margin` no report). Testes: `test_inms_base_row_shared_rule_honors_operator_direction`
  e `test_inms_base_conformidade_comes_from_shared_rule`. Suíte report+consolidate: 39 passed.