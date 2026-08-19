# 04 — MinC/MTur consolidation for ratio-shaped indicators

**What to build:** `scope.orgao` stops being fixed to `"MinC"` only (ticket 10's decision, revisited now that this ticket exists to handle the other órgão), and a consolidation step combines two same-indicator measurements — one per órgão — into a single `INMS_BASE` row, using `docs/spreadsheet.md`'s documented formula:

```
Resultado consolidado = (Numerador MinC + Numerador MTur) / (Denominador MinC + Denominador MTur)
```

No real MTur dataset exists yet (all 14 `/input` CSVs are MinC-only), so this ticket is verified entirely with synthetic dual-órgão fixtures — that's expected and fine; the goal is a correct, tested consolidation path ready for the day MTur data shows up, not a claim that real data was involved.

**Out of scope for this ticket:** the exception `docs/spreadsheet.md` calls out for per-asset disponibilidade indicators (1.4/1.5/1.14) — "o consolidado deverá seguir a fórmula específica prevista no Termo de Referência" — since that specific formula isn't identified anywhere in the read primary sources. Consolidation for those 3 indicators stays unimplemented; `report` should leave them un-consolidated (one row per órgão, as today) rather than silently applying the wrong formula.

**Blocked by:** None — can start immediately

**Status:** resolved

- [x] `Scope.orgao` accepts both `"MinC"` and `"MTur"` (was `Literal["MinC"]`)
- [x] `report` detects when two measurements share a contractual indicator number but differ in `orgao`, and for `ratio`/`segmented_ratio`/`count_difference` shapes (not the excepted per-asset disponibilidade indicators), consolidates them into one `INMS_BASE` row per the formula above — with per-órgão numerator/denominator still visible somewhere in the row or an adjacent detail, not just the blended result
- [x] The 3 excepted indicators (1.4, 1.5, 1.14) are left un-consolidated when both órgãos are present — one row per órgão, with a comment/flag noting the formula is unresolved
- [x] A synthetic fixture pair (same indicator, `orgao: MinC` and `orgao: MTur`, different numerator/denominator) proves the consolidated result matches the weighted formula, not a simple average
- [x] `docs/spec/inms-pipeline.md` §13's fog note is updated to reflect this ticket's resolution and the remaining per-asset exception
- [x] `mypy --strict` passes

## Answer

- `Scope.orgao` widened from `Literal["MinC"]` to `Literal["MinC", "MTur"]`, default unchanged
  (`"MinC"`) — no fixture needed updating.
- `pyauditor/excel/orgao_consolidation.py` (new module — kept separate from `report.py`, which
  already handles sheet-building/groups/glosas and didn't need a 4th concern folded in):
  `with_orgao_consolidation(summaries)` groups by `(contractual_id, asset)` — the `asset` key from
  ticket 01 keeps multi-asset indicators' MinC/MTur pairs consolidated independently per asset, not
  cross-mixed. Where both `"MinC"` and `"MTur"` are present, the shape is one of
  `ratio`/`segmented_ratio`/`count_difference` (not `external_catalog_sum` — no numerator/denominator
  to blend for a point sum), and the contractual_id isn't in the excepted set (`INMS 1.4`,
  `INMS 1.5`, `INMS 1.14`), it appends one synthetic `orgao: "Consolidado"` row built via
  `dataclasses.replace` on the MinC summary: `numerator`/`denominator` pooled per the weighted
  formula, `conforms` compared against the shared target, `penalty_points` the direct sum of both
  órgãos' already-computed penalties (documented as *not* a re-application of the degrau formula —
  the TR doesn't define one for the consolidated result).
- **Kept intentionally local to `INMS_BASE`:** `report.py`'s `build_report_workbook` only feeds the
  consolidated row list into the `INMS_BASE` sheet-building loop
  (`with_orgao_consolidation(summaries)`); group tabs and `GLOSAS` still iterate the original
  `summaries` list unchanged. Verified explicitly — `GLOSAS`' `Σ Pontos_NMS` sums only the 2 real
  measurements, not double-counted via the synthetic row's summed penalty.
- Small inline `_meets_target` helper inside the new module rather than importing
  `engine.strategies._target` (leading-underscore, package-private) from the `excel` layer — kept
  the two layers decoupled rather than reaching across a module boundary for two lines of math.
- `tests/test_orgao_consolidation.py` (8 tests) — weighted-not-averaged math (90/100 + 10/1000 →
  9.09%, not the simple-average 45.5%), conformance against target, penalty summing, the 3-indicator
  exception, `external_catalog_sum` exclusion, single-órgão pass-through (no-op), distinct
  consolidated `indicator_id`, and independent per-asset consolidation for multi-asset indicators.
  `tests/test_excel_report.py` gained an integration test proving `INMS_BASE` shows all 3 rows
  (MinC/MTur/Consolidado) while the group tab and `GLOSAS` total stay unaffected.
- `docs/spec/inms-pipeline.md` §10 rewritten to document the resolution and the formula; §13's fog
  list now has 2 items instead of 3 (multi-asset discovery dropped entirely — ticket 01 closed it),
  reworded to note the per-asset consolidation formula (1.4/1.5/1.14) as the item that's still
  genuinely unresolved.

Verified: `uv run mypy --strict src tests` → `Success: no issues found in 54 source files`. `uv run pytest -q` → `119 passed`. Ran the full `bootstrap → measure → report` pipeline via the installed CLI with a synthetic MinC (4/5=80%) + MTur (1/3=33.33%) pair: consolidated row correctly showed `(4+1)/(5+3) = 62.5%`, not the simple average (56.67%).
