# Map: pyauditor — production-readiness review

Label: wayfinder:map

## Destination

For each package under `src/pyauditor/`, a written findings report judging it against the `python-production-engineer` skill's checklist (correctness, typing, error handling, security, observability, tests, resilience, clarity) — then one synthesis pass that rolls all seven into a single priority-ordered punch list, using the skill's own severity order (correctness/data-loss → security → concurrency/idempotency → resilience → compatibility/operability → missing/fragile tests → performance → clarity/maintenance → style). This map produces findings, not fixes — any fix work spins off into its own follow-up ticket/map once the punch list exists.

## Notes

- Domain: pyauditor — see `CONTEXT.md` if present, else `docs/spec/inms-pipeline.md`.
- Every package ticket must call the Skill tool with `python-production-engineer`-equivalent rigor: read `.agents/skills/python-production-engineer/SKILL.md` in full and apply its "Regras de revisão de código" priority order and "Comportamentos proibidos" list verbatim.
- No greedy shortcuts: each package ticket reads every file in its package (not just the largest/newest one) before writing findings.
- Findings cite `file:line`. Severity per finding, not per package.
- This repo's own conventions override the skill's generic Google/AWS-inspired defaults where they conflict — cite `CLAUDE.md`, `docs/agents/unslop.md`, and existing code patterns (frozen dataclasses, `Final` constants, module docstrings citing spec/tickets) as the local standard.
- `.scratch/framework-audit/` is a prior, differently-scoped effort (spec-vs-implementation gap audit) — not the model for this map. This map is code-quality/production-readiness, not spec conformance.

## Decisions so far

- [Config package review](issues/01-config-package-review.md) — mypy/ruff clean; real gaps: raw `yaml.YAMLError` leaks uncaught past the actionable-error wrapping in `manifest.py`/`catalog.py`; `DatasetEntry.file/delimiter/encoding` missing `min_length=1` (empty `file=""` silently resolves to the data dir); no path-traversal/absolute-override validation on `file`/`csv` fields; `manifest.py` has zero test coverage of any failure path; plus dead code (`_RawManifest`) and a stale docstring.
- [Engine package review](issues/02-engine-package-review.md) — mypy clean; `ratio.py`'s `sum` aggregation uses bare `float()` instead of the codebase's `parse_decimal` convention, breaking on PT-BR comma-decimals; `quality_gates.py` does raw bracket access on a user-configurable `id_column`, raising `KeyError` instead of an actionable message; an `assert` guards external CSV shape instead of a real error; `external_catalog_sum.py` is the one strategy reaching into file I/O from the otherwise-pure calculation layer; confirmed real (not dead) test gaps in `_filters.py`/`_numbers.py`/`_target.py`/`precomputed_table.py` edge-case branches.
- [Excel package review](issues/03-excel-package-review.md) — mypy clean; silent cp1252 mangling of fiscal free-text, a dead `bold` variable making GLOSAS summary rows always-bold, no duplicate-header detection on hand-edited workbooks (the exact "broken shape" risk this package's invariant depends on), formula-injection risk on round-tripped fiscal decision text, `competencia` unvalidated at `report`/`consolidate` entry points, no workbook ever `.close()`d, non-atomic saves, zero tests for corrupted-ledger/corrupt-.xlsx/duplicate-header paths.
- [ROM package review](issues/04-rom-package-review.md) — mypy clean; `render.py` interpolates CSV-derived strings unescaped into Markdown tables (a stray `|` corrupts the ROM's table); `_as_float` lets `bool` pass as numeric; `IndicatorSummary(**raw)` does zero field-type validation at the JSON sidecar boundary, so a malformed value crashes uncaught deep in `excel/report.py`/`excel/consolidate.py` arithmetic rather than failing at load with a clear message; `_load_summaries` errors never name which file failed; 4 of 5 `_pooled_numerator_denominator` shape branches untested.
- [CLI package review](issues/05-cli-package-review.md) — ruff/mypy baseline confirmed unchanged (4 known pre-existing `main.py` findings); `competencia` format is validated only in `measure.py`, not `report.py`/`consolidate.py`/`main.py`, unlike the `_sanitize_indicator_id` pattern `measure.py` itself sets; most `run_*` functions only catch `OSError`, leaving other exceptions to escape uncaught with no top-level handler in `cli_main`; `main.py`'s dependency pre-flight checks bypass the `CHECKERS` registry for `bootstrap`/`measure`; the per-dataclass `_error` closures were judged load-bearing duplication, not worth a generic helper.
- [Orchestration package review](issues/06-orchestration-package-review.md) — ruff/mypy clean; confirmed the prior code-review's duplicated retry/skip/abort handling in `execute_run` still holds, verdict: worth a `_record_failure_and_decide` extraction; `state.py`'s `load_state` raises raw `JSONDecodeError`/`KeyError`/`TypeError` on a corrupted state file, uncaught to the CLI entrypoint; the pre-dispatch dependency-missing branch has 0% test coverage; no test anywhere exercises `orgao="both"`, the most complex path; idempotency on a fully-`done` re-run verified genuinely safe.
- [Interactive package review](issues/07-interactive-package-review.md) — ruff/mypy clean; **critical**: the design's "Ctrl+C encerra sem perder o preenchido" promise isn't implemented — every `RichQuestionaryProvider` method silently coerces `questionary`'s `None` (Ctrl+C/EOF) into an empty-looking answer instead of signaling cancellation, which can push `orgao=""` into `RunRequest` and makes Ctrl+C at the final confirm screen read as "No" (loops back into `collect_answers` instead of exiting); `on_failure`'s retry/skip/abort dispatch has zero test coverage; print-heavy design confirmed a justified, explicit exception to the logging rule.
- [Synthesis: prioritized findings](issues/08-synthesis-prioritized-findings.md) — 26 findings from tickets 01-07 merged into one priority-ordered punch list (6 P0-P1 correctness/data-loss items, 3 P2 security, 3 P3 resilience, 2 P4 operability, 7 P5 test gaps, 6 P6 clarity, 4 verified-no-action). Disposition: (a) the Ctrl+C bug (P0) — fix now, standalone, small enough to skip a map; (b) cross-package "boundary validation + error handling" (config/engine/orchestration/cli correctness+security+resilience items) — one follow-up effort; (c) excel package hardening — its own separate follow-up effort, split out because it holds the fiscal's irreplaceable hand-entered data and has the most findings of any package; test gaps ship with their fixes, not a separate effort; clarity items deferred as loose reference, no map. **This map's destination is reached — no tickets remain.**
  - Follow-up (a) shipped: commit `6d10b1b`.
  - Follow-up (b) shipped: commit `5abba6a` — all items done except item 13 (main.py/CHECKERS registry wiring, deliberately skipped as currently-inert).
  - Follow-up (c) shipped: commit `3f855ee`; the deferred non-atomic-save half of item 11 shipped separately in `22e4e87` (`atomic_write.py`).
  - P6 clarity items (21-26), initially deferred, picked up on request (2026-08-20) and all shipped: `428dc3c` (item 26, assert→explicit error), `94307dc` (item 21 orchestration half), `4169b57` (item 22, excel dedup), `02da2c5` (item 21 engine/rom half), `c08b9dd` (item 23, cli_main dispatch split), `236c9ac` (item 25, CHECKERS typing). Only item 13 stays deliberately unshipped — the one item confirmed inert with no live call site to protect.
  - **Every punch-list item now has a final disposition.** 250 tests passing (176 at review start), coverage 92.5% (88% at review start).

## Not yet specified

(none — map complete, destination reached at ticket 08)

## Out of scope

- Spec-vs-implementation conformance (already covered by `.scratch/framework-audit/`) — this map judges code quality against engineering standards, not against `docs/spec/inms-pipeline.md`.
- Implementing any fix this map's findings surface — that's a follow-up effort once the punch list (ticket 08) exists.
- `tests/` as its own reviewed package — test quality for each package's own code is part of that package's checklist ("testes ausentes ou frágeis"), not a ninth ticket.
