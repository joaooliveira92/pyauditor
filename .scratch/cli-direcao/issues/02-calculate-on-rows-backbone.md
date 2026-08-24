# 02 — Shared measurement backbone: `calculate_on_rows`

- **Type:** grilling
- **Status:** claimed
- **Blocked by:** —

## Question

Finding 2, severity high. `MeasureLoop._measure_categorias`
(measure_run.py:282-318) re-implements what `engine/pipeline.measure`
(pipeline.py:377-440) already owns — `QualityGateRunner`, `SHAPE_REGISTRY[shape]`,
two `hashlib.sha256` hashes, `MeasurementProvenance`, `MeasurementResult` —
~35 lines mirroring the backbone almost line-for-line, only because the rows are
a per-category filtered subset. This is the highest-risk logic in the system
duplicated.

Decision: the signature and body of a `calculate_on_rows(config, rows, ...)`
helper that `measure()` and the loop both call, replacing the mirror wiring.
Resolve it as: extract → make `measure()` route through it → make
`_measure_categorias` route through it → both green.

**Decided (approved):** (a) — extract the shared helper. **Hard gate:** the
suite stays green (599 passed baseline). Any behavioral drift in the
per-category path is a defect.

## Answer

(to be appended on resolution)