# 09 — Separar builders por aba do relatório

Type: task

**What to build:** os builders das abas do relatório por órgão deixam de viver todos no mesmo arquivo. As abas `cadastros`, `evidencias`, `inms_base` e `groups` ganham módulos próprios com seus helpers de linha e validação de célula (`excel/report/_cadastros.py`, `_evidencias.py`, `_inms_base.py`, `_groups.py`); `build_report_workbook` vira compositor.

**Blocked by:** 04 — glosa do relatório por órgão (mesmo arquivo; evita conflito de merge).

**Status:** ready-for-agent

- [ ] Workbook resultante com mesmas células, fórmulas e validações (semântica idêntica, não apenas "parece igual").
- [ ] `build_report_workbook` reduzido a composição.
- [ ] `uv run pytest`, `uv run ty check` e `uv run ruff check` verdes (suítes `test_excel_report.py` e `test_cli_report.py`).

## Contexto (do relatório SRP)

`excel/report.py` (699 físicas): `build_report_workbook` 92, `_build_glosas_sheet` 57, `compute_report_glosa` 47, mais `_build_cadastros_sheet`, `_build_evidencias_sheet`, `_build_inms_base_sheet`, `_build_group_sheets` e helpers de linha/validação. Segue o padrão já existente em `excel/inms_1_1/_sections_*` e `excel/sintetico/_sheets/`.