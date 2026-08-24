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

- *(none yet)*

## Not yet specified

- **Combined-ROM path**: `write_combined_roms` / `measure_combined.py` may need
  the same `calculate_on_rows` treatment once ticket 02 lands — the per-category
  and per-órgão merge both re-consume the backbone. Revisit after 02.
- **RunFlags scope**: whether the typed flags dataclass also adopts
  `report`/`consolidate` (they read fewer flags) or stays `run`-only.
- **CommandHandler revisited**: whether the per-command class idea (Q2b) is
  worth revisiting once `_dispatch_guard` lands, or is dead for this effort.

## Out of scope

- *(none yet — destination fixes scope; work beyond CLI coherence is a fresh
  effort, e.g. engine/pipeline behavior changes are not this map's route)*