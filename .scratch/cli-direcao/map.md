# CLI direction map

- **Status:** charting
- **Type:** wayfinder:map

## Destination

Make the CLI surface coherent: the three structural efforts land — the dispatch
boundary (`_dispatch_guard` + typed `RunFlags`), the shared measurement backbone
(`calculate_on_rows`), and the `MeasureLoop` split (`ResultSink`) — with the
mechanical findings (string-literal narrowing, help-string concatenations,
split.py re-exports) collapsing into the files they touch. No `CommandHandler`
hierarchy; no new behavior.

## Notes

- Domain: cli/ structural code-quality. All four review findings (1–7 of the
  code review) are in scope; this is the destination that resolves them.
- Skills: grilling + domain-modeling on every ticket; no research needed (no
  external knowledge). No research subagents.
- **Execution rides in the map** (effort override): resolving a ticket is
  design *then* implement, not just decide. This is a "change made in place"
  refactor.
- **Hard gate:** the suite must stay green after every ticket (baseline: 599
  passed, 34 skipped, 86% coverage). Ticket 02 (backbone) is the highest-risk
  logic in the system — measure twice, cut once.
- Do not verify with browsers or computer use; tests are the oracle.

## Decisions so far

<!-- one line per closed ticket: enough to judge relevance, then zoom the link -->

- [01 — Dispatch boundary: `_dispatch_guard` + `RunFlags`](issues/01-dispatch-guard-runflags.md)
  — `_dispatch_guard` collapses the verbatim competencia-validate block across
  the five dispatchers; `RunFlags` is **run-only**, carrying the six flags `run`
  re-casts, `output`/`on_warning` as Literals (finding 3). No `CommandHandler`.

## Not yet specified

- **Combined-ROM path**: `write_combined_roms` / `measure_combined.py` may need
  the same `calculate_on_rows` treatment once ticket 02 lands — the per-category
  and per-órgão merge both re-consume the backbone. Revisit after 02.

## Out of scope

- **CommandHandler revisited** — the per-command class idea (Q2b) is dead for
  this effort; ticket 01 settled `_dispatch_guard` + `RunFlags` as the shape.
  (The destination fixes scope; work beyond CLI coherence, e.g. engine/pipeline
  behavior changes, is a fresh effort.)