# 04 — Extrair glosa do relatório por órgão

Type: task

**What to build:** a computação da glosa do relatório por órgão deixa de viver no builder do workbook. `compute_report_glosa` de `excel/report.py` vira função pura num módulo próprio (`excel/report/_glosa.py`), consumida pelo builder da aba de glosas.

**Blocked by:** 01 — rede de testes da matemática financeira.

**Status:** resolved

- [x] `compute_report_glosa` move-se sem mudança de comportamento e sem tocar em openpyxl.
- [x] O builder da aba de glosas consome a função pura.
- [x] Assinatura pública preservada para os consumidores existentes.
- [x] `uv run pytest`, `uv run ty check` e `uv run ruff check` verdes.

## Contexto (do relatório SRP)

`excel/report.py` (699 físicas, 20 imports) mistura regra financeira e construção de abas. `compute_report_glosa` tem 47 linhas. Consumidores: `cli/report.py`, `test_excel_report.py`, `test_cli_report.py`.

## Answer

Criado `src/pyauditor/excel/_relatorio_glosa.py` (puro, sem `openpyxl`) com `compute_report_glosa` e `saldo_anterior_pct_de` (esta movida de `glosas.py`, pois só o `report` a consome — `_glosa_calcs` importa da `glosas.py` de origem; sem duplicação). O `__all__` expõe as duas.

`excel/report.py`:
- importa e reexporta `compute_report_glosa`/`saldo_anterior_pct_de` via `from pyauditor.excel._relatorio_glosa import ...` — o nome fica acessível por `pyauditor.excel.report` (API preservada, inclusive o `__all__`).
- `_build_glosas_sheet` continua consumindo `compute_report_glosa` e `houve_reincidencia`.
- Removidos imports/defs órfãos: `_summaries_for_glosa`, `compute_glosa`, `deduplicate_summaries`. Também limpei o `__all__` de `read_objetos` (símbolo que já tinha saído do arquivo num refactor anterior e ficou listado).

Sem mudança de comportamento: mesma `compute_report_glosa` (mesmo corpo, só mudou a residência), mesma aba `GLOSAS`. Consumidores externos (`cli/report.py`, `tests/test_report_glosa.py`) seguem importando de `excel.report` sem alteração.

Validação: `uv run pytest` 586 passados, cobertura 89.41% (gate 85% ok); `uv run ty check`, `uv run ruff check`, `uv run ruff format --check` e `uv run bandit` verdes.