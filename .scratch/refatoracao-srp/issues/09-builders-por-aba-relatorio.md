# 09 — Separar builders por aba do relatório

Type: task

**What to build:** os builders das abas do relatório por órgão deixam de viver todos no mesmo arquivo. As abas `cadastros`, `evidencias`, `inms_base` e `groups` ganham módulos próprios com seus helpers de linha e validação de célula (`excel/report/_cadastros.py`, `_evidencias.py`, `_inms_base.py`, `_groups.py`); `build_report_workbook` vira compositor.

**Blocked by:** 04 — glosa do relatório por órgão (mesmo arquivo; evita conflito de merge).

**Status:** resolved

- [x] Workbook resultante com mesmas células, fórmulas e validações (semântica idêntica, não apenas "parece igual").
- [x] `build_report_workbook` reduzido a composição.
- [x] `uv run pytest`, `uv run ty check` e `uv run ruff check` verdes (suítes `test_excel_report.py` e `test_cli_report.py`).

## Contexto (do relatório SRP)

`excel/report.py` (699 físicas): `build_report_workbook` 92, `_build_glosas_sheet` 57, `compute_report_glosa` 47, mais `_build_cadastros_sheet`, `_build_evidencias_sheet`, `_build_inms_base_sheet`, `_build_group_sheets` e helpers de linha/validação. Segue o padrão já existente em `excel/inms_1_1/_sections_*` e `excel/sintetico/_sheets/`.

## Answer

`excel/report.py` caiu de 646 → 175 linhas; os builders por aba foram para módulos próprios (ticket 09 SRP), cada um com suas constantes, helpers de linha e, quando aplicável, validações:

- `excel/_report_cadastros.py` — `build_cadastros_sheet`, `cadastros_row` (+ `_CADASTROS_COLUMNS`, `_config_sort_key`).
- `excel/_report_evidencias.py` — `build_evidencias_sheet`, `evidencias_row`, `_inline_validation_formula`, `_add_evidencias_validations` (validações de célula movidas junto).
- `excel/_report_inms_base.py` — `build_inms_base_sheet`, `inms_base_row`, `sort_key`.
- `excel/_report_groups.py` — `build_group_sheets`, `group_row` (usam `sort_key` e `GROUP_TABS`).
- `excel/_report_glosas.py` — `build_glosas_sheet` (consome `_relatorio_glosa.compute_report_glosa`/`saldo_anterior_pct_de` e `houve_reincidencia`).

`excel/report.py` virou compositor: importa os builders, monta as abas na ordem e reexporta as constantes `CADASTROS_SHEET`/`EVIDENCIAS_SHEET`/`INMS_BASE_SHEET`/`GLOSAS_SHEET` + `build_report`/`build_report_workbook`/`compute_report_glosa` (API pública intacta). Sem mudança de células/fórmulas/validações — suítes `test_excel_report.py`/`test_cli_report.py`/`test_external_catalog_sum.py` verdes sem alteração.

Validação: `uv run pytest` 586 passados, cobertura 89.65% (gate 85% ok); `uv run ty check`, `uv run ruff check`, `uv run ruff format --check` e `uv run bandit` verdes.