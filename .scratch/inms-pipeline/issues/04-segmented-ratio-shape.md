# 04 — `segmented_ratio` shape (INMS 1.2)

**What to build:** the second calculation shape — a ratio segmented into 3 priority categories (Alta/Média/Baixa), each with its own target and penalty rate, summed into a final penalty — registered alongside `ratio` in `SHAPE_REGISTRY`, with its own ROM renderer.

**Blocked by:** 02

**Status:** resolved

- [x] `SegmentedRatioCalculation` Pydantic model exists, discriminated on `shape: "segmented_ratio"`, modeling 3 categories each with numerator/denominator/target/penalty rate
- [x] `segmented_ratio` strategy computes each category's sub-ratio and sums the 3 penalties into a final penalty
- [x] ROM renderer for `segmented_ratio` shows sub-lines per category plus the sum, per spec.md §7
- [x] Running the pipeline against INMS 1.2's real `acceptance_test` (`/input/inms-001-02.csv`) produces the expected per-category and total results
- [x] `mypy --strict` passes on the new strategy module

## Answer

- **Correction to ticket 02 (important):** Anexo D writes INMS 1.2's penalty as an explicit
  formula — `INMS 1.2 (a) = (META − resultado) ÷ 0,1 × 20`, same shape for (b)/(c) with 15/10
  points — a *continuous linear* division, not a stepped/ceiling degrau. That contradicts the
  ceiling assumption ticket 02 made for INMS 1.1 (which only had prose, not a formula, to go on).
  Fixed `ratio.py`'s penalty math to match (see below) and updated the INMS 1.1 fixture's expected
  penalty from `225` to `222.14`.
- `pyauditor/config/models.py` — added `ColumnContains` (substring match) alongside `ColumnEquals`,
  unified as `Filter = ColumnEquals | ColumnContains` (Pydantic's smart union disambiguates on the
  distinct `equals`/`contains` field names, no discriminator needed). Added `SegmentedCategory`
  (name, denominator/numerator filters, `step_points`) and `SegmentedRatioCalculation` (`step_size_pct`
  + `categories`). `Calculation` is now a real discriminated union,
  `Annotated[RatioCalculation | SegmentedRatioCalculation, Field(discriminator="shape")]` — the
  single-member placeholder from ticket 02 is gone. `IndicatorConfig.penalty` became `Penalty | None`
  since `segmented_ratio` carries its own per-category penalty math instead of the shared
  base/step/step-size block `ratio` uses.
- `pyauditor/engine/strategies/_target.py` (new) — `meets_target`/`shortfall`, factored out of
  `ratio.py` so `segmented_ratio.py` doesn't duplicate it.
- `pyauditor/engine/strategies/_filters.py` (new) — `filter_rows`, handling both `ColumnEquals` and
  `ColumnContains`; both `ratio.py` and `segmented_ratio.py` use it.
- `pyauditor/engine/strategies/segmented_ratio.py` — `SegmentedRatioStrategy` computes each
  category's numerator/denominator/result, a per-category penalty
  (`max(shortfall, 0) / step_size_pct * category.step_points`), and sums them.
  `CalculationResult.result_pct`/`conforms` (shared across all shapes) have no single Anexo-D-defined
  meaning for 3 categories against one shared target — documented as an assumption: `result_pct` is
  the pooled ratio (Σnumerators/Σdenominators), `conforms` is true only when total penalty is zero.
  The authoritative per-category breakdown lives in `memoria["categories"]`, which the ROM renderer
  reads instead. Registered in `SHAPE_REGISTRY["segmented_ratio"]`.
- `pyauditor/rom/render.py` — added `render_segmented_ratio_memoria` (Markdown table: categoria,
  numerador, denominador, resultado, penalidade + sum line); also fixed the generic template's
  penalty format from `{:.0f}` to `{:.2f}` since penalties are no longer guaranteed integers under
  the corrected linear formula.
- **Modeling assumption (real data):** Anexo D has no dedicated priority column — priority is
  embedded in the free-text `SLA` field (e.g. `"(CIT) Requisição - Alta 04 horas"`,
  `"(URA) Triagem - Alta 30 mim"`). All 11 distinct `SLA` values in the real
  `/input/inms-001-02.csv` contain exactly one of Alta/Média/Baixa, no overlaps, covering 100% of
  the 1514 rows — so `ColumnContains` substring matching on `SLA` is used for category filters.
  This is plausible but, like INMS 1.8's dataset schema (ticket 11), not confirmed by any primary
  source as the official mechanism — documented in the fixture YAML's comment.
- `tests/fixtures/configs/inms-1.2.yaml` + `tests/test_segmented_ratio.py` — real acceptance test
  against `/input/inms-001-02.csv` (all 3 categories conform: Alta 524/533, Média 461/464, Baixa
  505/517, pooled 98.41% ≥ 95% meta, zero penalty). Since the real data doesn't exercise the penalty
  branch, added a synthetic fixture (`tmp_path`, inline CSV) putting one category below target to
  prove the linear-penalty math independent of production data.

Verified: `uv run mypy --strict src tests` → `Success: no issues found in 24 source files`.
`uv run pytest -q` → `9 passed`.
