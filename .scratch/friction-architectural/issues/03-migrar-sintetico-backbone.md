# 03 — Migrar `write_sintetico_workbook` para o backbone

**What to build:** `excel/sintetico.write_sintetico_workbook` deixa de reimplementar
o pipeline (load_config → resolve → read_raw_csv → filtra período → gates) e passa a
usar o backbone `measurement_source()`. As abas do sintético continuam produzindo o
mesmo workbook, incluindo `_write_nao_ativado_sheet` quando o dataset não existe e as
mensagens de warning por INMS.

Este passo elimina a fronteira package-private furada: `sintetico.py` não precisa mais
importar `engine.strategies._filters`/`_numbers`/`_target` para reimplementar as etapas
que o backbone entrega prontas (incluindo as linhas cruas intermediárias que o sintético
precisa no meio do pipeline).

**Blocked by:** 02

**Status:** ready-for-agent

- [x] `write_sintetico_workbook` usa `measurement_source()` e não reimplementa resolve/lê/filtra/gates.
- [x] Imports package-private de `engine.strategies` removidos de `sintetico.py`.
- [x] Comportamento das abas preservado (mesmo workbook, mesmas abas `_nao_ativado`, mesmos warnings) — `test_excel_sintetico.py` verde.

## Comments

- 2026-08-22 — Implementado. `write_sintetico_workbook` chama
  `measurement_source(..., emit_empty_window_warning=False)` — sintetico
  continua nunca emitindo o WARN de janela vazia. `filter_rows`/
  `parse_decimal`/`meets_target`/`safe_pct` agora são re-exportados por
  `engine/strategies/__init__.py` (público) em vez de `sintetico.py`
  alcançar `_filters`/`_numbers`/`_target` (package-private) diretamente.
  Mudança de comportamento deliberada e não coberta por teste antes: quando
  `period_column` está declarado mas ausente do header, a aba agora degrada
  (mesmo tratamento dos demais erros do loop) em vez de silenciosamente
  calcular sobre linhas não filtradas. `test_excel_sintetico.py`: 18/18
  verdes; suíte completa sem novas falhas (66 pré-existentes, mesmas de
  antes do ticket 02).