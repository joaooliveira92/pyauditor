# 01 — Dispatch boundary: `_dispatch_guard` + `RunFlags`

- **Type:** grilling
- **Status:** claimed
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

*(to be appended on resolution)*