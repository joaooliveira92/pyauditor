# 11 — Full 14-indicator acceptance smoke test

**What to build:** the parametrized smoke test from spec.md §5 — `pytest.mark.parametrize` running all 14 real `acceptance_test` cases (across all 4 shapes) against their real `/input` CSVs, proving the engine matches contractual reality end to end.

**Blocked by:** 04, 05, 06, 07

**Status:** resolved

- [x] A single parametrized test discovers all 14 indicator configs (1.1–1.14) and their `acceptance_test` blocks, running each through the full pipeline (config parse → quality gates → calculation)
- [x] All 14 cases pass against the real production CSVs in `/input`
- [x] Test failures report which indicator and which field (numerator, denominator, result, penalty) diverged, not just a generic assertion failure
- [x] This test does not depend on CLI subcommands — it drives the engine directly, so it can run before or independently of tickets 08–10

## Answer

`tests/test_full_acceptance_smoke.py` — `discover_configs(CONFIG_DIR)` (the same function `measure`'s CLI uses) finds all 14 `tests/fixtures/configs/inms-1.*.yaml` fixtures at module load; `pytest.mark.parametrize` runs each through `measure(config, data_dir=INPUT_DIR)` directly against the real `/input` CSVs — no CLI subprocess, no ROM/JSON I/O. A shape-agnostic assertion block checks every field the config's `acceptance_test.expected` actually sets (`result_pct`, `conforms`, `penalty_points` always; `numerator`/`denominator`, `categories` [segmented_ratio], `qrc`/`qcsi`/`cni` [count_difference], `total_points` [external_catalog_sum] only when present), each with an explicit `f"{indicator}: {field} — expected X, got Y"` message — verified this actually surfaces both the right indicator and field by deliberately corrupting `inms-1.1.yaml`'s expected `penalty_points` and confirming the failure read `INMS 1.1: penalty_points — expected 999.0, got 222.14...` before reverting. A second test (`test_all_14_indicators_are_discovered`) guards against silently losing a fixture (asserts the discovered set is exactly `INMS 1.1`..`INMS 1.14`).

This test is intentionally additional to, not a replacement for, the individual per-shape test files (`test_ratio_tracer_bullet.py`, `test_segmented_ratio.py`, `test_count_difference.py`, `test_external_catalog_sum.py`, `test_remaining_ratio_indicators.py`) — those also cover synthetic edge cases (degrau math, dedup, hard-failure paths) the real `/input` data can't exercise (several real CSVs are empty — 1.3, 1.8, 1.9, 1.10 — so their "real" acceptance tests are the documented degenerate cases, already covered elsewhere).

Verified: `uv run mypy --strict src tests` → `Success: no issues found in 47 source files`. `uv run pytest -q` → `90 passed`.
