# 10 — `is_final_month` chega ao consolidate

**What to build:** o parâmetro `is_final_month` deixa de ser morto e passa a controlar o
fim do rollover de glosa também no `consolidado.xlsx`.

Hoje `--final-month` (CLI) e `RunRequest.final_month` chegam ao `report` (que desliga o
rollover de glosa), mas nenhum caminho passa `True` para `build_glosas`/
`build_consolidated_workbook`. Resultado: no mês final do contrato, `report.xlsx`
respeita o fim do rollover mas `consolidado.xlsx` continua transportando saldo para o
mês seguinte — os dois artefatos financeiros divergem silenciosamente.

**Blocked by:** None — can start immediately.

**Status:** done

- [x] `is_final_month` é passado por um caminho real (CLI/orchestration) até `build_glosas`/`build_consolidated_workbook`.
- [x] `consolidado.xlsx` no mês final não transporta saldo de glosa para o mês seguinte; `report.xlsx` e `consolidado.xlsx` divergem do mesmo jeito no mês final.
- [x] `test_excel_consolidate.py` exercita `is_final_month=True` (e o caminho CLI correspondente).

## Comments

- 2026-08-22 — Implementado. `is_final_month` percola o caminho inteiro do consolidate:
  `cli/main.py` ganhou `--final-month` no parser e `ConsolidateRequest.is_final_month`;
  `run_consolidate` recebe `is_final_month` e repassa a `build_consolidated_workbook`;
  `orchestration/run.py` repassa `request.final_month`. Testes:
  `test_is_final_month_reaches_compute_glosa` e o parametrizado
  `test_saldo_rolado_honors_final_month` em `test_excel_consolidate.py` (mês final ⇒
  `saldo_rolado_pct == 0.0`, senão 10pp), mais `test_run_consolidate_forwards_is_final_month_to_workbook`
  em `test_cli_consolidate.py`. Suíte alvo (35) verde.