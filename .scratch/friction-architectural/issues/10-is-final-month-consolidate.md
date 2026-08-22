# 10 — `is_final_month` chega ao consolidate

**What to build:** o parâmetro `is_final_month` deixa de ser morto e passa a controlar o
fim do rollover de glosa também no `consolidado.xlsx`.

Hoje `--final-month` (CLI) e `RunRequest.final_month` chegam ao `report` (que desliga o
rollover de glosa), mas nenhum caminho passa `True` para `build_glosas`/
`build_consolidated_workbook`. Resultado: no mês final do contrato, `report.xlsx`
respeita o fim do rollover mas `consolidado.xlsx` continua transportando saldo para o
mês seguinte — os dois artefatos financeiros divergem silenciosamente.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] `is_final_month` é passado por um caminho real (CLI/orchestration) até `build_glosas`/`build_consolidated_workbook`.
- [ ] `consolidado.xlsx` no mês final não transporta saldo de glosa para o mês seguinte; `report.xlsx` e `consolidado.xlsx` divergem do mesmo jeito no mês final.
- [ ] `test_excel_consolidate.py` exercita `is_final_month=True` (e o caminho CLI correspondente).