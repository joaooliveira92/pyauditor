Type: research

Status: resolved

## Question

Review `src/pyauditor/rom/` (`render.py`, `summary.py`) against the `python-production-engineer` skill's checklist (`.agents/skills/python-production-engineer/SKILL.md`). Read every file in the package in full before writing findings.

Judge specifically:

- `summary.py`'s JSON sidecar serialization (`IndicatorSummary.to_dict()`/`IndicatorSummary(**raw)` round-trip used across `cli/report.py` and `cli/consolidate.py`) — is the round-trip validated, or does a malformed/stale sidecar JSON raise a cryptic `TypeError` deep in `IndicatorSummary(**raw)` instead of an actionable message? This is a real seam other packages depend on (`cli/report.py:_load_summaries`, `cli/consolidate.py:_load_summaries`) — worth judging as a boundary, not just internal code.
- `render.py`'s Markdown templating — any injection-adjacent risk from unescaped user-controlled strings (capa fields, contractual IDs) landing in the ROM, given the ROM is meant to be a formal audit artifact?
- Coverage: `rom/summary.py` showed 64% coverage as of the last full test run — confirm whether the gap is meaningful (error paths) or incidental.

Report each finding as `file:line — severity — description — suggested fix`, ordered by the skill's priority list. Run `uv run ruff check src/pyauditor/rom` and `uv run mypy src/pyauditor/rom` first, note the baseline, don't re-report what's already clean.

## Answer

### Tooling baseline

- `uv run mypy src/pyauditor/rom`: clean, no issues.
- `uv run ruff check src/pyauditor/rom`: 9 pre-existing style findings, all line-length (E501) and ambiguous-unicode-character (RUF001, the `−`/`×` glyphs used in the interpretative formulas) — not re-reported individually below; see "style" item at the end.
- `pytest --cov=pyauditor.rom`: `render.py` 86%, `summary.py` 64% (matches the number cited in the ticket).

Files read in full: `src/pyauditor/rom/__init__.py` (empty), `src/pyauditor/rom/summary.py`, `src/pyauditor/rom/render.py`, plus the two consuming call sites `src/pyauditor/cli/report.py` (`_load_summaries` L47-52, `run_report` L55-141) and `src/pyauditor/cli/consolidate.py` (`_load_summaries` L50-55, `run_consolidate` L58-118).

### Findings (priority order per skill)

**1. Correctness / data integrity**

- `src/pyauditor/rom/render.py:32` (`render_segmented_ratio_memoria`), `:58` (`render_external_catalog_sum_memoria`), `:76` (`render_precomputed_table_memoria`), `:207` (`render_rom`'s `rejected_table`) — Medium — each interpolates a string that ultimately traces back to input-CSV content (`c['name']`, `o['descricao']`, `row.reason`) directly into a Markdown `| ... |` table cell with no escaping of `|` or newlines. A stray `|` or embedded newline in that upstream data silently shifts/breaks the table's column alignment in what is meant to be a formal, auditable ROM document — the failure mode is a misrepresented audit record, not a crash, so it can go unnoticed. Not remote-code-execution-style injection (Markdown here isn't executed/rendered by a script-capable renderer), but it is unescaped external data landing in structured output, which is the injection-adjacent risk the ticket asked about. Fix: add a small `_md_cell(s: str) -> str` helper (`s.replace("|", "\\|").replace("\n", " ")`) and route all four sites through it.
- `src/pyauditor/rom/render.py:106-130` (`_render_identificacao`, `_render_responsaveis`, via `_capa_value`) — Low — same root cause for capa fields (Fiscal técnico, Competência, etc.), which are free-text Excel cells filled by órgão staff. Lower severity than the table case since these render as bullet-list lines, not table cells, but an embedded newline or leading `#`/`-` could still shift the Markdown structure (fake heading/bullet). Fix: same escaping helper, or at minimum strip embedded newlines in `_capa_value`.
- `src/pyauditor/rom/summary.py:80-83` (`_as_float`) — Low — `isinstance(value, int | float)` also matches `bool` (bool is an `int` subclass in Python), so a stray JSON `true`/`false` in a numeric memoria field (e.g. `numerator`) is silently coerced to `1.0`/`0.0` instead of being rejected. Fix: `isinstance(value, int | float) and not isinstance(value, bool)`.

**2. Security / privacy**

- No findings. Nothing in `rom/` does SQL, subprocess, `eval`/`exec`, deserializes pickle/yaml-unsafe formats, or logs secrets. `json.loads` is the only "deserialization," and it's the standard-library safe form. The Markdown outputs aren't executed by anything, so the unescaped-string findings above are filed as correctness/data-integrity, not security.

**3. Concurrency / idempotency**

- No findings. `rom/render.py` and `rom/summary.py` are pure functions over immutable (`frozen=True`) dataclasses; no shared mutable state, no I/O, nothing to serialize access to.

**4. Resilience / failure behavior — this is the sharpest boundary issue in the package**

- `src/pyauditor/cli/report.py:117-124` (`build_report(...)`, only `except OSError`) and `src/pyauditor/cli/consolidate.py:101-103` (`build_consolidated_workbook(...)`, no try/except at all) — High — `IndicatorSummary(**raw)` in both `_load_summaries` (`report.py:47-52`, `consolidate.py:50-55`) performs **no field-type validation**: a plain `@dataclass` constructor accepts any object for any field, so a stale/hand-edited/cross-version sidecar JSON with a wrong-typed value (e.g. a string where `result_pct`/`target_value` is expected) passes `_load_summaries` without error — the surrounding `except (OSError, json.JSONDecodeError, TypeError)` only catches missing/extra/renamed keyword arguments, not wrong value types. The bad value then reaches `excel/report.py`/`excel/consolidate.py` arithmetic (`round(summary.result_pct, 2)`, `summary.target_value - summary.result_pct`, etc.) several calls later, **outside** any of the two CLI functions' error handling, and crashes with an unhandled `TypeError` and a raw traceback instead of the actionable `_error(...)` path the rest of `run_report`/`run_consolidate` uses. This is exactly the "malformed/stale sidecar JSON raises a cryptic error deep in the code" risk the ticket flagged — it's just one hop further downstream than `IndicatorSummary(**raw)` itself. Fix: validate field types at the `_load_summaries` boundary (manual per-field checks, or a `__post_init__` on `IndicatorSummary` that raises a domain error with the offending field name), so bad sidecars fail at load time with an actionable message.
- `src/pyauditor/cli/report.py:47-52` and `src/pyauditor/cli/consolidate.py:50-55` (`_load_summaries`) — Medium — even for the errors that *are* caught (missing/extra fields via `TypeError`), the exception is only caught once around the whole `for summary_path in sorted(roms_dir.glob("*.json"))` loop, at the call site (`report.py:83-85`, `consolidate.py:86-87`). The resulting message (`f"falha ao ler sumários de medição em {competencia_dir}: {exc}"`) never names which of the (potentially dozens of) `*.json` files under `roms_dir` was the culprit — the raw `TypeError` text ("IndicatorSummary.__init__() missing 1 required positional argument: 'hard_failure'") gives no file to bisect from. Fix: catch per-file inside the loop and re-raise with the path, e.g. `raise ValueError(f"sumário inválido em {summary_path}: {exc}") from exc`.

**5. Compatibility / operability**

- No additional findings beyond the two above.

**6. Missing / fragile tests**

- `src/pyauditor/rom/summary.py:64-77,83` (64% coverage, confirmed via `pytest --cov=pyauditor.rom --cov-report=term-missing`) — Medium — the gap is not incidental error-path noise: it's the `segmented_ratio` branch (L64-70), the `count_difference` branch (L72-73), the `external_catalog_sum`/`precomputed_table` fallback (L75-77), and `_as_float`'s non-numeric-return branch (L83) of `_pooled_numerator_denominator` — 4 of 5 shape branches of real, distinct pooling logic. No test calls `summarize()` for any shape other than `ratio` (the only direct caller in the test suite is `tests/test_multi_asset_discovery.py:72`, which exercises `ratio`); the other shape test files (`test_segmented_ratio.py`, `test_count_difference.py`, `test_external_catalog_sum.py`, `test_precomputed_table.py`) construct `IndicatorSummary` by hand or don't touch `summarize()`/`_pooled_numerator_denominator` at all. A bug in the segmented_ratio sum or in the count_difference `(QCSI, QRC) → (numerator, denominator)` mapping would go undetected. Fix: add one unit test per shape asserting `summarize(result).numerator`/`.denominator` against the expected pooled values.

**7. Performance**

- No findings — package is small, pure, and non-hot-path (runs once per indicator per measurement run).

**8. Clarity / maintenance**

- `src/pyauditor/rom/render.py:30,53,71` (`assert isinstance(categories, list)` / `assert isinstance(occurrences, list)`) and `:141` (`assert config.target is not None`) — Low — using `assert` to validate an internal contract with the engine layer (`calculation.memoria`'s shape, `config.target`'s presence). `assert` statements are stripped under `python -O`, which would silently turn a would-be clear failure into a raw `KeyError`/`TypeError` further down with no context — inconsistent with the skill's "falha explicita" principle, though low risk since this repo doesn't run with `-O`. Fix: replace with explicit `if not isinstance(...): raise TypeError(...)`, or better, give `CalculationResult.memoria` a discriminated type per shape so the check is enforced by the type system instead.

**9. Style**

- Already flagged by `ruff check src/pyauditor/rom` and not re-reported per-line: 4× E501 (line length, `render.py:25,32,189`, `summary.py:68-69`) and 3× RUF001 (ambiguous unicode `−`/`×` glyphs, `render.py:48,153-155`, used intentionally in the human-facing formula text). `mypy` is clean.
