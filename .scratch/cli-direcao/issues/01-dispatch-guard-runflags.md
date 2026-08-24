# 01 — Dispatch boundary: `_dispatch_guard` + `RunFlags`

- **Type:** grilling
- **Status:** resolved
- **Blocked by:** —

## Question

Findings 1 and 4. Five `_dispatch_*` functions (measure, split, report,
consolidate, run — main.py:110-349) repeat the same ritual: `extract_*_request`
→ `validate_competencia` → print + `return 2` → `setup_logging(_run_log_path(...))`
→ per-órgão loop. And every flag read re-derives the runtime type with
`cast(object, getattr(args, ...)) + bool(...)` (main.py:325-348, 375-384).

Resolve: the shape of a thin `_dispatch_guard`-style helper (validate + log
setup, collapsing the near-verbatim scaffolding) and a typed `RunFlags`
dataclass assembled once, so the `run` dispatch reads plain fields instead of
re-casting the Namespace. Fold in finding 3 (the `'json' if x == 'json' else
'text'` Literal re-encoding) — the dataclass should carry the Literal directly.

**Decided (approved):** (a) — helper + dataclass, no `CommandHandler`. The
remaining decision is the exact field set and which dispatch functions adopt
`RunFlags` (see map's Not-yet-specified on run-only vs report/consolidate).

## Answer

Design (a) landed in `cli/main.py`: `_dispatch_guard` + typed `RunFlags`, no
`CommandHandler`.

- **`_dispatch_guard(competencia)`** (main.py:113) collapses the verbatim
  `validate_competencia → print → return 2` block shared by all five
  dispatchers. `setup_logging` stays in each dispatcher: its `log_path` and
  loop placement differ per command (split/bootstrap log per-órgão inside the
  loop; measure/report/consolidate/run log once).
- **`RunFlags`** (main.py:123), **run-only**. measure/report/consolidate/split
  already read their booleans through typed `*Request` dataclasses; folding
  `is_final_month` into RunFlags would duplicate them. Carries exactly the six
  flags `run` re-derives: `output`/`on_warning` as Literals (folding finding
  3, the `'json' if x == 'json' else 'text'` re-encoding) plus `force`/
  `clean`/`final_month`/`strict` as bools.
- **`_dispatch_run`** assembles `RunFlags` once and reads plain fields,
  dropping the five `bool(cast(object, getattr(args, ...)))` / Literal
  re-casts.

Resulting field set: `output: OutputFormat = 'text'`, `force: bool = False`,
`strict: bool = False`, `final_month: bool = False`, `clean: bool = False`,
`on_warning: OnWarningMode = 'continue'`.

Suite green after the refactor: 599 passed, 34 skipped, 86.45% coverage —
identical to the baseline. The `ty` diagnostic for `logging.py` is pre-existing
and unrelated.

Not-yet-specified items resolved by this ticket: **RunFlags scope** (settled:
run-only) and **CommandHandler revisited** (settled: dead for this effort —
moved to the map's Out of scope). **Combined-ROM path** stays foggy pending
ticket 02.