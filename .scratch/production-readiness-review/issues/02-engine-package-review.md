Type: research
Status: resolved

## Question

Review `src/pyauditor/engine/` (`pipeline.py`, `quality_gates.py`, `strategies/_filters.py`, `strategies/_numbers.py`, `strategies/_target.py`, `strategies/precomputed_table.py`) against the `python-production-engineer` skill's checklist (`.agents/skills/python-production-engineer/SKILL.md`). Read every file in the package in full before writing findings.

Judge specifically:

- This is the domain core (indicator measurement math) — is it genuinely free of I/O/infrastructure concerns, or has presentation/file-I/O crept in?
- Correctness of numeric edge cases: division by zero, empty datasets, `None` propagation through the calculation shapes (`ratio`, `segmented_ratio`, `count_difference`, `external_catalog_sum`).
- Repeated Switches: does dispatch on calculation "shape" happen in more than one place with the same cases?
- Error handling: does a malformed CSV/config surface an actionable error, or propagate a raw pandas/stdlib exception up to the CLI boundary?
- Test coverage against the coverage report (`uv run pytest` prints per-file coverage) — `strategies/_filters.py` and `strategies/_numbers.py` showed under 80% coverage as of the last full test run; confirm whether the uncovered lines are edge cases worth a test or genuinely dead code.

Report each finding as `file:line — severity — description — suggested fix`, ordered by the skill's priority list. Run `uv run ruff check src/pyauditor/engine` and `uv run mypy src/pyauditor/engine` first, note the baseline, don't re-report what's already clean.

## Answer

### Tooling baseline

`uv run mypy src/pyauditor/engine` — clean, "Success: no issues found in 13 source files".

`uv run ruff check src/pyauditor/engine` — 8 findings, all style/hygiene, not re-litigated below beyond listing them:
- F401 unused import: `pipeline.py:16` (`load_manifest`), `strategies/_filters.py:10` (`DurationAtMost`), `strategies/_numbers.py:10` (`Final`)
- E501 line too long (>100): `strategies/base.py:18`, `strategies/external_catalog_sum.py:26`, `strategies/precomputed_table.py:33`, `strategies/precomputed_table.py:70`
- UP047 generic function should use type params: `strategies/base.py:24` (`narrow_calculation`)

`uv run pytest -q --no-cov`: 170 passed, 34 skipped. `--cov=pyauditor.engine`: `_filters.py` 60%, `_numbers.py` 75%, `_target.py` 82%, `precomputed_table.py` 78%, `pipeline.py` 86%, `quality_gates.py` 98%.

### Findings

**Correctness / data-loss**

- `src/pyauditor/engine/strategies/ratio.py:61,67,75` — HIGH — the `aggregation: sum` path parses numeric columns with bare `float(row[col])` instead of `parse_decimal` (`strategies/_numbers.py`). Every other numeric-reading strategy (`precomputed_table.py`) routes through `parse_decimal` specifically because the real datasets are PT-BR exports with comma decimals (`"99,451"`) — `_numbers.py`'s own module docstring says so. `float("5,5")` raises `ValueError` uncaught, so any `sum_numerator_column`/`sum_denominator_extra_column`/`sum_numerator_subtract_column` value that happens to be a decimal (not just an integer count) blows up with a raw stdlib exception instead of returning `nan`/being skipped like the rest of the codebase. It's currently caught generically at the CLI boundary (`cli/measure.py:169`, `except Exception`) so it doesn't crash a whole run, but it silently fails that one indicator with an unhelpful message ("could not convert string to float: '5,5'") instead of the intended graceful nan-skip. Fix: replace the three `float(row[...])` calls with `parse_decimal(row[...])` and skip on `isnan`, matching `precomputed_table.py`'s pattern.

- `src/pyauditor/engine/quality_gates.py:38` — MEDIUM — `RejectedRow(row_id=row[self._id_column], ...)` uses bracket indexing on `id_column`, which is user-configurable YAML (`source.id_column`, default `"Nº Solicitacao"`). A config typo or a CSV whose header doesn't match produces a raw `KeyError` instead of an actionable "id_column X not found in this CSV's header" error. Every other lookup in this file uses `.get(...)`. Caught generically upstream, but the surfaced message is just the bare key repr. Fix: `row.get(self._id_column, "<sem id>")`, or validate `id_column in fieldnames` once up front (in `pipeline.load_rows` or `measure`) and raise a clear domain error before the per-row loop.

- `src/pyauditor/engine/pipeline.py:81` — LOW/MEDIUM — `assert reader.fieldnames is not None` guards an external-data condition (empty/headerless CSV), not an internal invariant. `assert` is the wrong tool here: it's stripped under `python -O`, and `AssertionError` isn't an actionable message for "CSV has no header row". Fix: raise a domain-appropriate `ValueError` with the CSV path in the message.

**Security** — no findings. No `shell=True`, the one `subprocess.run` call (`pipeline.py:64`, `git rev-parse`) uses an argument list with `timeout=5` and is fully exception-guarded; no secrets/PII in logs or error strings observed in this package.

**Concurrency / idempotency** — no findings. Pipeline is synchronous, single-pass, no shared mutable state across calls; `measure()` is a pure function of its inputs plus wall-clock time (see clarity note below on `datetime.now()`).

**Resilience**

- `src/pyauditor/engine/strategies/external_catalog_sum.py:19` — MEDIUM — answers the ticket's "is the domain core free of I/O" question: `calculate()` calls `load_anexo_e_catalog()` directly, which reads a packaged YAML resource via `importlib.resources` (`config/catalog.py`). It's read-only, `lru_cache`d, and hermetic (packaged, not user-supplied path), so the practical failure risk is low — but it's the one strategy in `strategies/` that reaches out to infrastructure (file I/O) from inside what the rest of the package treats as pure calculation logic (`ratio.py`, `segmented_ratio.py`, `count_difference.py`, `precomputed_table.py` all take only `config`+`rows`). It also means this strategy can't be tested with a fake catalog without monkeypatching a module-level cached function. Fix: thread the catalog in as a parameter (either on `CalculationStrategy.calculate` for this shape, or resolved once in `pipeline.measure` and passed down), keeping `strategies/` free of imports from `config.catalog`.

**Compatibility / operability**

- `src/pyauditor/rom/summary.py:61-72` (outside the reviewed package, but directly answers the ticket's "repeated switch" question) — LOW — `_pooled_numerator_denominator` re-implements a shape dispatch (`if shape == "ratio"`, `"segmented_ratio"`, `"count_difference"`) that duplicates the case list already enumerated once in `engine/strategies/__init__.py`'s `SHAPE_REGISTRY`. Adding a 6th shape (or renaming one) requires updating both places with nothing to catch a missed case. Within `engine/` itself, shape dispatch is clean — `SHAPE_REGISTRY` is the single dispatch point, and each strategy's own `narrow_calculation` assert is a one-shape check, not a repeated switch. Fix (out of scope for this ticket's package, flagging for the punch list): derive the numerator/denominator keys from each shape's own `CalculationResult.memoria` shape instead of a second string-keyed `if` chain in `rom/summary.py`.

**Missing / fragile tests**

- `src/pyauditor/engine/strategies/_filters.py:29-32,41-45` — MEDIUM — `ColumnIn` matching and the entire `DurationAtMost`/`_parse_duration_seconds` path, including its malformed-input branches (wrong segment count, non-digit parts), are 0% covered. This is exactly the "malformed CSV" edge case the ticket calls out: `_parse_duration_seconds`'s docstring itself warns it would mis-parse a `D:HH:MM:SS` days-prefixed duration (used elsewhere in the availability CSVs) — there's no test proving the intended "returns `None` -> row filtered out" behavior for either that case or plain garbage input.
- `src/pyauditor/engine/strategies/_numbers.py:22-23` — MEDIUM — `parse_decimal`'s `except ValueError: return float("nan")` branch — the actual malformed-numeric-data safety net every ratio/precomputed_table computation relies on — is untested. No test asserts `parse_decimal("abc")` (or empty string, or a stray thousands separator) returns `nan` and that callers skip on it.
- `src/pyauditor/engine/strategies/_target.py:14` — LOW — `meets_target`'s and `shortfall`'s `<=`-operator branch is untested (only `>=` is exercised by existing tests). Any indicator config using a "no more than X%" target is unverified by the current suite.
- `src/pyauditor/engine/strategies/precomputed_table.py:54-62,80` — MEDIUM — real business-logic branches, not dead code: the explicit `penalty_column` read (including its isnan-guard-to-0 fallback), the non-percent point-total penalty (`max(value - target, 0)`), and the unweighted arithmetic-mean headline fallback (used when rows lack numerator/denominator columns) have no direct test.

**Performance** — no findings; dataset sizes are competência-scale CSVs, no evidence of a hot loop needing optimization.

**Clarity / maintenance**

- `src/pyauditor/engine/pipeline.py:188` — LOW — `datetime.now()` is neither timezone-aware nor injectable (no clock parameter), so `MeasurementProvenance.processed_at` can't be asserted deterministically in tests and is ambiguous across DST/timezone boundaries. Low impact since it's provenance-only metadata, but the skill calls for injectable clocks specifically for testability. Fix: accept an optional `now: Callable[[], datetime]` (defaulting to `datetime.now`) on `measure()`, or at least use `datetime.now(UTC)`.

**Style** — covered by the ruff baseline above; no additional style findings beyond what tooling already flags.
