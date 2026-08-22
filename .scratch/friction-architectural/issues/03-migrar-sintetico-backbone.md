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

- [ ] `write_sintetico_workbook` usa `measurement_source()` e não reimplementa resolve/lê/filtra/gates.
- [ ] Imports package-private de `engine.strategies` removidos de `sintetico.py`.
- [ ] Comportamento das abas preservado (mesmo workbook, mesmas abas `_nao_ativado`, mesmos warnings) — `test_excel_sintetico.py` verde.