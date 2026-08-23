# 04 — Extrair glosa do relatório por órgão

Type: task

**What to build:** a computação da glosa do relatório por órgão deixa de viver no builder do workbook. `compute_report_glosa` de `excel/report.py` vira função pura num módulo próprio (`excel/report/_glosa.py`), consumida pelo builder da aba de glosas.

**Blocked by:** 01 — rede de testes da matemática financeira.

**Status:** ready-for-agent

- [ ] `compute_report_glosa` move-se sem mudança de comportamento e sem tocar em openpyxl.
- [ ] O builder da aba de glosas consome a função pura.
- [ ] Assinatura pública preservada para os consumidores existentes.
- [ ] `uv run pytest`, `uv run ty check` e `uv run ruff check` verdes.

## Contexto (do relatório SRP)

`excel/report.py` (699 físicas, 20 imports) mistura regra financeira e construção de abas. `compute_report_glosa` tem 47 linhas. Consumidores: `cli/report.py`, `test_excel_report.py`, `test_cli_report.py`.