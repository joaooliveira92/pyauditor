# 05 — `count_difference` shape (INMS 1.10)

**What to build:** the third calculation shape — `CNI = QRC − QCSI`, a count difference rather than a ratio, with a fixed penalty per missing unit (not a percentage-based degrau) — registered in `SHAPE_REGISTRY`, with its own ROM renderer.

**Blocked by:** 02

**Status:** resolved

- [x] `CountDifferenceCalculation` Pydantic model exists, discriminated on `shape: "count_difference"`, modeling `QRC`, `QCSI`, and a fixed per-unit penalty
- [x] `count_difference` strategy computes `CNI = QRC − QCSI` and the resulting fixed penalty (no target/degrau logic — this shape has neither)
- [x] ROM renderer for `count_difference` shows the terms of the difference (`QRC`, `QCSI`, `CNI`), per spec.md §7
- [x] Running the pipeline against INMS 1.10's real `acceptance_test` (`/input/inms-001-10.csv`) produces the expected `CNI` and penalty
- [x] `mypy --strict` passes on the new strategy module

## Answer

- **Dataset-schema discovery (same class of fog as ticket 11/INMS 1.8):** the real
  `/input/inms-001-10.csv` is **empty — header only** (the same generic ITSM header shared by the
  `ratio`-shaped indicators), zero data rows. Anexo D defines `QRC`/`QCSI` (recommended vs.
  implemented security controls) but never says how a control gets recorded in a dataset — same gap
  as INMS 1.8's occurrence catalog. This isn't blocking (the shape and its math are fully specified
  by Anexo D regardless of how QRC/QCSI get counted), but it means the "real acceptance_test"
  against `/input/inms-001-10.csv` is degenerate (`QRC=QCSI=CNI=0`) — it only proves the pipeline
  runs against the real file without breaking, not that the calculation is correct. The actual
  penalty math is proven by two synthetic fixtures instead (below).
- `pyauditor/config/models.py` — `CountDifferenceCalculation` (`shape: "count_difference"`,
  `recommended_filter: Filter | None` for QRC, `implemented_filter: Filter` for the QCSI subset,
  `penalty_per_unit`), joining the `Calculation` discriminated union (now 3 members). Extended
  `AcceptanceTestExpected` with optional `qrc`/`qcsi`/`cni` fields.
- `pyauditor/engine/strategies/count_difference.py` — `CountDifferenceStrategy` computes
  `QRC`/`QCSI`/`CNI = QRC − QCSI` via the shared `filter_rows` helper, `penalty_points = max(CNI, 0) *
  penalty_per_unit` (no degrau/target math — Anexo D's "1000 pontos a cada controle não
  implementado" is already a flat per-unit rate), `conforms = CNI <= 0`. `result_pct` (required by
  the shared `CalculationResult` for the ROM's generic section) is defined as
  `QCSI/QRC × 100` — matching Anexo D's "= 100%" meta framing — with `100.0` as the vacuous case
  when `QRC == 0`. Registered in `SHAPE_REGISTRY["count_difference"]`.
- `pyauditor/rom/render.py` — `render_count_difference_memoria` shows the three terms of the
  difference (`QRC`, `QCSI`, `CNI`) per spec.md §7.
- `tests/fixtures/configs/inms-1.10.yaml` — real config against the empty real CSV, with a comment
  explaining why its acceptance test is degenerate. `tests/test_count_difference.py` — two synthetic
  fixtures (`tmp_path`) prove the actual math: 5 recommended/3 implemented → `CNI=2`, penalty 2000,
  non-conforming; and an all-implemented case → `CNI=0`, penalty 0, conforming.

Verified: `uv run mypy --strict src tests` → `Success: no issues found in 26 source files`.
`uv run pytest -q` → `13 passed`.
