# 05 — Cohere split.py re-exports

- **Type:** grilling
- **Status:** claimed
- **Blocked by:** —

## Question

Findings 6. `cli/split.py` imports `excel.sintetico` (split.py:51) and
re-imports contracts aliases (split.py:73-74) to re-export public API — e.g.
`SplitCategoriaOutcome = contracts.SplitCategoriaOutcome` — so the
commands/contracts types are reachable under two names. Minor drift risk.

Decision: the cleanest way to keep a stable public API under one name per type —
either re-export directly from `pyauditor.commands.contracts` with a single
canonical name, or drop the alias and have callers import from source. Low
severity; smallest change that kills the two-name drift.

## Answer

(to be appended on frontier)