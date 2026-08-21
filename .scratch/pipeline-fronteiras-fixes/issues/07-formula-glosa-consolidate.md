# 07 — Corrigir a fórmula de glosa duplicada em `consolidate.py`

**Origem:** [Excel report→consolidate boundary review](../../pipeline-fronteiras-review/issues/05-excel-report-consolidate-boundary.md)

**What to build:** `excel/consolidate.py::build_glosas` reimplementa a fórmula de glosa do zero em vez de reusar `glosas.compute_glosa` (já usada por `report.py`): ignora `saldo_anterior_pct` (rollover mensal persistido em `glosa_historico.json`), soma MinC+MTur contra um teto único de 30% em vez de por-órgão, e ignora `is_final_month`/reincidência. O "Valor Glosa" do consolidado — que alimenta `CALCULO_PAGAMENTO` — pode divergir silenciosamente do valor já oficial e publicado no relatório por-órgão. Fazer `build_glosas` reusar `glosas.compute_glosa` (ou a lógica equivalente) em vez de reimplementar.

**Blocked by:** None — can start immediately.

- [ ] O "Valor Glosa" no consolidado é idêntico ao valor já publicado no relatório por-órgão, para o mesmo período e os mesmos dados
- [ ] Rollover mensal (`saldo_anterior_pct`) e teto por-órgão são respeitados no consolidado
- [ ] Teste de regressão comparando glosa do relatório por-órgão vs. glosa do consolidado para o mesmo cenário
