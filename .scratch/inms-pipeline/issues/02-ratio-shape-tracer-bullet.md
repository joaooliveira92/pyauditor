# 02 — `ratio` shape end-to-end tracer bullet (INMS 1.1)

**What to build:** the whole pipeline proven for one indicator, end to end: a `ratio`-shaped YAML config parses via the Pydantic discriminated union, `QualityGateRunner` validates the CSV data (rejecting bad rows with ID + reason), the `ratio` calculation strategy computes numerator/denominator/result against the target, and the generic ROM template renders a Markdown memória de cálculo using the `ratio` renderer — all driven by INMS 1.1's real `acceptance_test` from `/input/inms-001-01.csv`.

This ticket establishes the pattern (config → quality gates → calculation → ROM) that every later shape and the CLI build on. It only needs to prove `count_distinct` aggregation — `sum` and `precomputed` variants are covered by ticket 07.

**Blocked by:** 01

**Status:** resolved

- [x] `RatioCalculation` Pydantic model exists, discriminated on `shape: "ratio"`, with an `aggregation` field supporting at least `count_distinct`
- [x] `QualityGateRunner` parses the CSV, applies `quality_gates.checks`, and produces a rejected-rows list with ID + violated rule
- [x] `ratio` strategy computes numerator/denominator/result and compares against `target` (operator + threshold), producing degrau-based penalty per the YAML's `penalty` block
- [x] Generic ROM template renders: cabeçalho, população, rejeições, memória de cálculo (via `ratio` renderer), resultado vs meta — matching the shape in spec.md §7.1
- [x] Running the pipeline against INMS 1.1's real `acceptance_test` (from `docs/spec/inms-pipeline.md` §2 / `/input/inms-001-01.csv`) produces the expected result and penalty
- [x] `mypy --strict` passes on the new modules — no `dict[str, Any]` or `# type: ignore` in the calculation path

## Answer

Built the full tracer bullet:

- `pyauditor/config/models.py` — `IndicatorConfig` with `Indicator`, `Scope` (orgao fixed `"MinC"`), `Source`, `QualityGates` (checks discriminated on `type`: `NotNullCheck` | `InSetCheck`), `RatioCalculation` (`shape: Literal["ratio"]`, `aggregation: Literal["count_distinct"]`, numerator/denominator column filters), `Target`, `Penalty`, `AcceptanceTest`. Note: `Calculation` is a plain alias to `RatioCalculation` for now, not yet a `Union` — Pydantic's discriminated union needs 2+ members, so the `Field(discriminator="shape")` wiring is deferred until ticket 04 adds `SegmentedRatioCalculation`. `RatioCalculation` itself already carries the `shape` literal discriminator field, so no rework is needed when the union grows.
- `pyauditor/engine/quality_gates.py` — `QualityGateRunner.run()` walks each row against the configured checks (first violation wins) and returns `QualityGateReport(accepted, rejected)`, `rejected` entries carrying row id + human-readable reason.
- `pyauditor/engine/strategies/ratio.py` — `RatioStrategy` filters rows (denominator filter, then numerator filter within it), computes `result_pct`, checks conformance against `target.operator`/`target.value`, and computes the degrau penalty as `base_points + ceil(shortfall / step_size_pct) * step_points` when non-conforming. The exact rounding rule for partial degraus isn't specified at this granularity in Anexo D — documented as an assumption (ceiling, with an epsilon to absorb float noise) in the module docstring and in the fixture YAML's comment.
- `pyauditor/engine/pipeline.py` — `load_config()` (YAML→Pydantic) and `measure()` (load CSV → quality gates → strategy from `SHAPE_REGISTRY`) tie it together; `config_dir` for CSV resolution is passed separately from the config file's own location, so fixtures can live in the repo while pointing at the git-ignored `/input` data.
- `pyauditor/rom/render.py` — generic template (cabeçalho, população, rejeições, memória de cálculo, resultado vs meta) with a `_MEMORIA_RENDERERS` dict keyed by shape; `render_ratio_memoria` is the first entry.
- `tests/fixtures/configs/inms-1.1.yaml` — real INMS 1.1 config (Anexo D Tabela 28: meta ≥98%, 165 pontos + 20 por 0,1% abaixo) with an `acceptance_test` block computed against the real `/input/inms-001-01.csv` (175 rows, 171 "S" → 97.71%, 3 degraus → 225 pontos penalty).
- `tests/test_ratio_tracer_bullet.py` — end-to-end test against real production data (skipped if `/input` isn't present locally, since it's git-ignored PII) plus a ROM-shape assertion. `tests/test_quality_gates.py` — synthetic unit test proving the rejection path (not exercised by INMS 1.1's clean real data).

Verified: `uv run mypy --strict src tests` → `Success: no issues found in 17 source files`. `uv run pytest -q` → `4 passed`.

**Correction (during ticket 04):** Anexo D's formula for INMS 1.2 is written out explicitly as
`(META − resultado) ÷ 0,1 × pontos` — a continuous division, no ceiling. That confirms the
"ceiling to a whole degrau" assumption made above for INMS 1.1 was wrong; the penalty is linear and
can be fractional. `ratio.py`'s `_linear_penalty` was rewritten accordingly (shared math factored
into `engine/strategies/_target.py`), and the INMS 1.1 fixture's expected penalty updated from
`225` to `222.14` (`165 + (0.2857/0.1)×20`). See ticket 04's answer for detail.
