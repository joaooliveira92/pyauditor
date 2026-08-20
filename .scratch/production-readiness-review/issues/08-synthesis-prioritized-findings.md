Type: grilling
Status: resolved
Blocked by: 01, 02, 03, 04, 05, 06, 07 (all resolved)

## Question

All seven packages under `src/pyauditor/` have individual findings reports (tickets 01-07). Roll them into a single priority-ordered punch list, using the `python-production-engineer` skill's own severity order: correctness/data-loss → security/privacy → concurrency/idempotency/transactions → resilience under failure → compatibility/operability → missing or fragile tests → performance (only with evidence) → clarity/maintenance → style.

Also surface cross-package patterns a single-package lens would miss — e.g. the same Result-construction shape repeated across all four `cli/*.py` command files (flagged independently in ticket 05), or a shared "actionable error at a JSON boundary" gap that shows up in both `rom/summary.py` (ticket 04) and `orchestration/state.py` (ticket 06). Where two package tickets flag what's really one systemic issue, merge them into a single punch-list item that names every affected file.

For each punch-list item, decide: worth its own follow-up implementation ticket/map now, or explicitly deferred (with the reason)? This is a human judgment call — grill the user on any item where severity or priority against real project constraints (deadline, fiscal's actual pain points, TR compliance risk) isn't obvious from the code alone.

Write the final punch list into this ticket's Answer. This map's destination is reached once this ticket resolves — it does not spawn implementation work itself, only decides what to spin off.

## Answer

Merged from tickets 01-07 (26 individual findings, 3 verified "no finding" passes), ordered by the skill's severity list. Cross-package duplicates are merged into one item naming every affected file.

### P0 — Correctness / data-loss, Critical

1. **[interactive] Ctrl+C doesn't honor the "encerra sem perder o preenchido" promise — silently corrupts the flow instead of exiting.** `provider.py:54-87` — every `RichQuestionaryProvider` method turns `questionary`'s `None` (Ctrl+C/EOF) into a normal-looking empty answer (`""`/`[]`/`False`), which can push `orgao=""` into `RunRequest` (dispatches against the wrong directories, no error) and makes Ctrl+C at the final confirm screen read as "No" — looping back into `collect_answers` instead of exiting (`flow.py:66-68,73-104`). This is a bug in code from this session, not legacy debt.

### P1 — Correctness / data-loss, High/Medium

2. **[config + rom + orchestration] No validation/actionable-error wrapping at three separate JSON/YAML boundaries — same systemic gap, three files.**
   - `config/manifest.py:75`, `config/catalog.py:75` — raw `yaml.YAMLError` on malformed YAML.
   - `orchestration/state.py:42-49` — raw `JSONDecodeError`/`KeyError`/`TypeError` on a corrupted run-state file, uncaught to the CLI entrypoint.
   - `rom/summary.py` (`IndicatorSummary(**raw)`) — zero field-type validation; a wrong-typed sidecar value crashes uncaught in `excel/report.py`/`excel/consolidate.py` arithmetic several calls later, not at load time.
   Same fix shape in all three: wrap the parse, raise a domain exception with the offending path/field, `raise ... from exc`.
3. **[excel] Multiple real bugs in `consolidate.py`.** Silent cp1252 mangling of fiscal free text (`:158-161`, replaces non-Windows-1252 chars with `?`, no warning); dead `bold` variable makes every GLOSAS summary row render bold instead of just two (`:389`, visible cosmetic bug); duplicate-header collision in a hand-edited workbook silently reads decisions from the wrong column (`:120-155`, `capa.py:143-160`) — this is the exact "broken shape" risk the package's re-run invariant depends on; dead `tipo_col`/`status_col` mask hardcoded validation ranges that would silently desync if columns are reordered (`report.py:205-223`).
4. **[engine] `ratio.py:61,67,75`'s `sum` aggregation uses bare `float()` instead of the codebase's `parse_decimal` convention** — breaks on PT-BR comma-decimal values (`"5,5"` raises `ValueError`) that every other numeric-reading strategy already handles correctly.
5. **[rom] `render.py:32,58,76,207`** interpolates CSV-derived strings unescaped into ROM Markdown tables — a stray `|` or newline silently corrupts the audit table's alignment in what's meant to be a formal record.

### P2 — Security

6. **[excel] `consolidate.py:353-373`** — formula-injection risk: fiscal-entered free text (Justificativa, Observação do Gestor) round-trips into new cells with no check for a leading `=+-@`, becoming a live formula next time the workbook opens. This is the one column set explicitly designed to persist and accumulate across the contract's lifetime.
7. **[cli + excel] `competencia` format is validated only in `measure.py`, not `report`/`consolidate`/`main.py`.** Flagged independently by both the CLI review (`cli/report.py:81`, `cli/consolidate.py:42,45`, `cli/main.py:222-253`) and the excel review (same call sites) — one fix: hoist `_COMPETENCIA_RE` into a shared helper, validate once per entry point.
8. **[config] `manifest.py`/`models.py:72`** — `file`/`csv` fields aren't validated against path traversal or absolute-path override at the config boundary. Low exploitability (trusted, version-controlled config) but cheap to close.

### P3 — Resilience

9. **[orchestration] `run.py:226-244` vs `:269-287`** — confirmed (2nd review) the pre-dispatch and post-dispatch retry/skip/abort branches are still duplicated; verdict from the reviewer: worth extracting a `_record_failure_and_decide` helper now, not deferring — the pre-dispatch copy also has 0% test coverage (finding 15 below), so the two can silently drift.
10. **[cli] `report.py`/`consolidate.py`/`bootstrap.py`** only catch `OSError` around their core calls; other exception types escape uncaught with no top-level handler in `cli_main`. `measure.py:169`'s broad `except Exception` is the one command that closes this gap correctly, but undocumented as intentional.
11. **[excel] No try/except around workbook reads** (`read_capa_fields`/`read_existing_decisions`), unlike the JSON ledger's graceful degradation; saves are non-atomic (`workbook.save`, `write_historico`) — a crash mid-write can brick the *next* run's ability to read back decisions, compounding finding 11's missing try/except.

### P4 — Compatibility / operability

12. **[excel] No workbook is ever `.close()`d anywhere in the codebase** (confirmed via grep).
13. **[cli] `main.py`'s dependency pre-flight checks bypass the `CHECKERS` registry** for `bootstrap`/`measure` (harmless today — both are no-ops — but drifts from `orchestration/run.py`'s pattern of always going through the registry).

### P5 — Missing / fragile tests

14. **[config] `manifest.py` has zero test coverage of any failure path** (contrast: `catalog.py` has 5).
15. **[orchestration] `orgao="both"` is never exercised by any test** — the most complex path in the package (cross-órgão cascade into shared `consolidate`); the pre-dispatch failure branch is also 0% covered.
16. **[interactive] `on_failure`'s retry/skip/abort dispatch has zero test coverage**; `_validate_competencia`'s own branches are never exercised (the fake provider ignores `validate`).
17. **[rom] 4 of 5 shape branches of `summarize()`/`_pooled_numerator_denominator` are untested** — only `ratio` is covered.
18. **[engine] `_filters.py`'s `ColumnIn`/`DurationAtMost` malformed-input paths, `_numbers.py`'s nan fallback, `_target.py`'s `<=` branch, `precomputed_table.py`'s explicit-penalty-column branch** — all real logic, confirmed not dead code.
19. **[excel] No test for corrupted ledger, corrupt `.xlsx`, or the duplicate-header collision** (finding 3).
20. **[cli] The `competencia`-validation gap (finding 7) has no regression test to build a fix on.**

### P6 — Clarity / maintenance (mostly optional, non-blocking)

21. **[engine + rom + orchestration] Shape/type dispatch duplicated in three places**: `engine/strategies/__init__.py`'s `SHAPE_REGISTRY` vs. `rom/summary.py`'s separate if-chain (same shape list, two places to update); `orchestration/summary.py`'s `_result_for`/`_artifact_line` each independently re-discriminate the same 4 `CommandResult` subtypes.
22. **[excel] `_UNIT_BY_SHAPE` dict and sheet/row-writing helpers are byte-identical duplication** between `report.py` and `consolidate.py` — genuinely incidental, unlike `_inms_base_row` (different column sets by design, should stay separate).
23. **[cli] `main.py`'s `cli_main` still mixes several change reasons per subcommand** despite the `_extract_*_request` split — not urgent at current size.
24. **[config] Dead code (`_RawManifest`), a docstring claiming `ValidationError` propagates when it doesn't.**
25. **[cli] `cli/dependencies.py`'s `CHECKERS: dict[str, Callable[..., DependencyCheck]]`** erases each checker's real signature — optional `Protocol`-per-checker would let mypy catch a wrong-arity call.
26. **[rom + engine] `assert`-based invariant checks on external data** (`rom/render.py:30,53,71,141`, `engine/pipeline.py:81`) — stripped under `python -O`, not currently a real risk (repo doesn't run with `-O`) but the wrong tool for "external CSV shape is unexpected."

### Verified — no finding, no action needed

- **[cli]** The `_error` closure duplication across `bootstrap.py`/`measure.py`/`report.py`/`consolidate.py` — load-bearing (each closes over a differently-shaped frozen dataclass); a generic helper would need `**kwargs` and lose mypy field-safety. Leave as-is.
- **[orchestration]** Idempotency on a fully-`done` re-run — verified genuinely safe (zero writes/dispatches), confirmed by test.
- **[interactive]** Protocol conformance (`RichQuestionaryProvider`/`FakeInteractionProvider` vs. `InteractionProvider`) — confirmed clean by mypy strict across `src`+`tests`; print-heavy design is a justified, now explicitly-documented exception to the logging rule.
- **[excel]** Float vs. `Decimal` for money/points — informational only, not worth introducing `Decimal` at this system's realistic magnitudes; one design choice (aggregate glosa computed independently from unrounded totals, not by summing displayed rows) is correct but worth a one-line comment so it doesn't read as a bug to an auditor.

### Disposition — what spins off, what's deferred

Grilled with the user (2026-08-20); all three questions confirmed with the recommended answer.

1. **P0 (item 1, the Ctrl+C bug) — fix now, standalone, own small effort. DONE (2026-08-20).** `InteractionCancelled` exception added to `interactive/provider.py`; every `RichQuestionaryProvider` method raises it instead of coercing `None` into an empty answer; `flow.py::run_guided_flow` catches it once, shows a clean message, exits `130`; `collect_answers`'s recursion converted to a `while` loop (removes the "Ctrl+C at final confirm loops forever" trap structurally, not just by fixing the symptom); `FakeInteractionProvider` gained a `CANCEL` sentinel for scripting cancellation in tests. 6 new tests (`test_interactive_provider.py`, plus 2 in `test_interactive_flow.py`). 176 tests passing, ruff/mypy clean. Small blast radius (`interactive/provider.py` only), the guided flow is brand new and hasn't seen a real competência yet, and it directly contradicts a promise made in the flow's own opening screen. Not worth a wayfinder map — sharp enough to go straight to implementation.
2. **P1-P3 correctness/security/resilience (items 2, 4, 5, 7, 8, 9, 10, 13) — one cross-package "boundary validation + error handling" follow-up effort. DONE (2026-08-20), except item 13 (deliberately skipped).** Scattered across `config`, `engine`, `orchestration`, `cli`, but the same fix *shape* throughout: validate/wrap at a boundary, raise an actionable domain exception with `from exc`. Bundling avoided re-deriving the same pattern five times as separate efforts.
   - Item 2: `config/manifest.py`/`catalog.py` wrap `yaml.YAMLError`; `rom/summary.py`'s `IndicatorSummary` gained `__post_init__` field-type validation (rejects a wrong-typed sidecar at load time, not deep in `excel/` arithmetic) plus per-file error naming in both `_load_summaries`; `orchestration/state.py` gained `RunStateCorrupted` + self-healing (a corrupted run-state file logs a warning and starts fresh instead of crashing).
   - Item 4: `engine/strategies/ratio.py`'s `sum` aggregation now routes through `parse_decimal` (PT-BR comma-decimals), matching the rest of the codebase.
   - Item 5: `rom/render.py` gained `_md_cell()`, applied to every CSV-derived Markdown table cell.
   - Item 7: `validate_competencia()` hoisted into `cli/results.py`, applied to `report`/`consolidate` (measure already had it).
   - Item 8: `config/_paths.py`'s `reject_unsafe_relative_path()`, applied to `DatasetEntry.file` and `Source.csv`.
   - Item 9: `orchestration/run.py`'s duplicated retry/skip/abort handling collapsed into one `record_failure_and_decide()` closure; added tests for the pre-dispatch failure branch and the `orgao="both"` cross-órgão cascade (both previously untested) — `orchestration/run.py` coverage went 80% → 94%.
   - Item 10: `bootstrap.py`/`report.py`/`consolidate.py` now catch `Exception` (not just `OSError`) around their core calls, converting to an error Result instead of leaking a raw traceback; `measure.py`'s existing broad catch got the documenting comment finding 8 asked for.
   - Item 13 (main.py's pre-flight bypassing `CHECKERS` for bootstrap/measure) — **skipped**, per the review's own verdict ("harmless today — both are no-ops"); not worth the added dispatch complexity for a currently-inert gap.
   - Also picked up while in these files: config's dead `_RawManifest` class removed, stale `catalog.py` docstring fixed, `tests/test_manifest.py` added (was previously zero-coverage).
   - 45 new tests across the touched packages; full suite 223 passing (up from 176), coverage 91.6% (up from 88%), mypy/ruff clean on everything touched (only the 4 pre-existing `test_glosas.py` errors remain, confirmed unrelated).
3. **Excel package (items 3, 6, 11, 12) — its own separate follow-up effort, split out from #2. DONE (2026-08-20), except the non-atomic-save half of item 11 (deliberately deferred).** Reasoning: most findings of any package (6 of 12 in P1-P3), holds the fiscal's irreplaceable hand-entered decision columns (the one thing this whole review's "must survive a hand-edited workbook" invariant exists to protect), and its bugs (dead `bold` var, cp1252 mangling, duplicate-header collision, no atomic saves) are self-contained to `excel/` — no shared root cause with #2's boundary-validation theme.
   - Item 3: dropped the cp1252 round-trip in `consolidate.py`'s `_clean()` entirely (UTF-8 works fine in modern Excel; nothing in the codebase depended on the mangling); fixed the dead `bold` variable so only "Total de Pontos"/"Valor Glosa" render bold in the GLOSAS summary (was every row); `read_existing_decisions`/`read_capa_fields` now raise a clear `ValueError` naming the duplicate column/label instead of silently keeping the last occurrence; the dead `tipo_col`/`status_col` in `report.py` were left as-is (flagged Low, not touched this pass — the hardcoded ranges they mask are correct today).
   - Item 6: the 5 fiscal decision columns in GLOSAS (Reincidência/Justificativa/Número da Ocorrência/Decisão Fiscal/Observação do Gestor) are now written with `number_format = "@"` (text), blocking formula injection on round-tripped free text without altering the displayed value.
   - Item 11 (partial): `read_capa_fields`/`read_existing_decisions` calls in `cli/report.py`/`cli/consolidate.py` now wrapped in `try/except Exception`, converting a corrupt/non-`.xlsx` file into an error Result instead of an uncaught `zipfile.BadZipFile`. Non-atomic `workbook.save()`/`write_historico` — **deferred**: fixing this needs a write-to-temp-then-`os.replace()` helper shared across `capa.py`/`report.py`/`consolidate.py`/`glosas.py`, a small enough scope to be its own tightly-focused ticket rather than folded in here; noted for a future pass, not urgent (single-operator CLI, low crash-during-save likelihood).
   - Item 12: every `load_workbook()`/freshly-built `Workbook()` this session touched now closes in a `finally` (openpyxl's `Workbook` has no context-manager protocol — confirmed by inspection, correcting the earlier review's suggested `with load_workbook(...) as wb:` fix, which wouldn't actually work).
   - 11 new tests (`test_excel_consolidate.py`, `test_capa.py`, `test_cli_report.py`, `test_cli_consolidate.py`) covering each regression fixed. Full suite 230 passing, coverage 91.7%, mypy/ruff clean on everything touched.
4. **P5 tests (items 14-20) — no separate effort; each fix in #1-#3 ships with its own regression test.** This is how the individual package reviews already scoped most of these findings ("fix should ship a test, not standalone").
5. **P6 clarity/maintenance (items 21-26) — deferred, left as loose reference in this ticket, no map.** None block anything; lowest risk to pick up opportunistically rather than schedule now.

**This map's destination is reached.** Two follow-up efforts are ready to be chartered when the user wants to start them: (a) Ctrl+C fix — small enough to skip wayfinder, straight to implementation; (b) "boundary validation + error handling" across config/engine/orchestration/cli; (c) excel package hardening. (b) and (c) are candidates for their own `/wayfinder` maps if they need further breakdown, or could go straight to a ticket list if the scope already feels sharp enough — user's call.

