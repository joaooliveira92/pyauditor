# 10 — `GLOSAS` tab — glosa calculation

**What to build:** the monetary glosa calculation from spec.md §12, aggregating `Pontos_NMS` across all 14 indicators for the month, applying `Ajuste_NMS(%) = min(30%, Σ Pontos_NMS × 0.001%)`, computing `valor da glosa = Ajuste_NMS(%) × valor-base`, tracking the 30% cap and rollover of any excess to the next month's fatura, written to the `GLOSAS` tab.

**Blocked by:** 09

**Status:** resolved

- [x] Glosa calculation sums `penalty_points` across all indicators measured for the competência (Anexos D and E combined), computes the percentage once over the total (not per-indicator then summed), per spec.md §12.1
- [x] The 30% cap is enforced; any excess is tracked as a rollover amount for the next competência (except the contract's final month, which has no next month to roll to)
- [x] `GLOSAS` tab is populated with the columns listed in spec.md §12.3 (competência, Σ Pontos_NMS, percentual de ajuste, valor-base, valor da glosa, teto atingido?, saldo rolado) — the fiscal-manual columns from `docs/spreadsheet.md` §Aba 10 are left blank
- [x] `valor-base` is treated as the total monthly contract value, per the convention adopted in spec.md §12.2
- [x] `mypy --strict` passes on the new module

## Answer

- `pyauditor/excel/glosas.py` (new) — `compute_glosa(total_points, valor_base, is_final_month=False)` → `GlosaResult`. `percentual_ajuste = min(total_points × 0.001, 30.0)`; `teto_atingido = raw_pct > 30.0`; `valor_da_glosa = percentual_ajuste/100 × valor_base` (or `None` if `valor_base` is `None` — the percentage/teto are still fully computable without it, only the monetary conversion needs it); `saldo_rolado_pct = raw_pct − 30.0` when over cap, forced to `0.0` when `is_final_month=True` per the ticket's "no next month to roll to" rule.
- **`valor-base` source:** `pyauditor/excel/capa.py` gained `read_valor_mensal_vigente(path)`, reading the "Valor mensal vigente" cell `bootstrap` already creates (blank until the fiscal técnico fills it in by hand) — this is the concrete source for spec §12.2's `valor-base` convention (total monthly contract value), closing the loop between `bootstrap` and `report` rather than requiring a new, redundant input.
- `pyauditor/excel/report.py` — `build_report_workbook`/`build_report` gained `valor_base: float | None` and `is_final_month: bool` parameters; a `GLOSAS` sheet is now always built (one row, using exactly the 7 columns spec §12.3 lists — not the fuller 16-column `docs/spreadsheet.md` §Aba 10 layout, which has several fiscal-manual and per-indicator columns that don't apply to a month-level aggregate and were out of this ticket's explicit column list). `Σ Pontos_NMS do mês` sums `penalty_points` across every summary passed in, in one shot — never per-indicator percentages summed afterward, matching spec §12.1's explicit ordering. Also updated `INMS_BASE`'s glosa-related columns' comments (`Ocorrência de glosa`, `Percentual de glosa`, `Valor-base`, `Valor da glosa`) — these stay blank not because ticket 10 "hadn't happened yet" (the old comment) but because glosa is a month-level aggregate with no defined per-indicator allocation in spec §12; attributing a share of it to each row would be fabrication.
- `pyauditor/cli/report.py` — `run_report` now calls `read_valor_mensal_vigente(capa_path)` and passes it through to `build_report`; logs an informational (non-fatal) note when the capa's value is still blank, since `GLOSAS` still gets a valid percentual/teto without it, just no monetary `valor da glosa`.
- Rollover is a single-month calculation, not a running balance — `saldo_rolado_pct` reports *this* month's excess as the amount that should roll into *next* month's fatura, but nothing in this ticket persists that number and folds it into a following `report` run (there's no cross-competência state store yet). Documented as a scope boundary in `glosas.py`'s docstring, not silently assumed away — implementing true multi-month accumulation would need a persistence mechanism outside the wayfinder map's current destination.

Verified: `uv run mypy --strict src tests` → `Success: no issues found in 49 source files`. `uv run pytest -q` → `103 passed`. Ran the full `bootstrap → measure → report` pipeline via the installed CLI against all 14 real fixtures with a manually-filled `Valor mensal vigente` (R$250.000): `Σ Pontos_NMS = 580.067,26`, `percentual de ajuste` correctly capped at 30% (raw would've been ~580%), `valor da glosa = R$75.000` (30% × 250.000), `teto atingido = S`, `saldo rolado ≈ 550,07` p.p.
