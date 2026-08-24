# 03 — Split `MeasureLoop`: `ResultSink` collaborator

- **Type:** grilling
- **Status:** claimed
- **Blocked by:** 02 — both refactor `_measure_categorias`; extract the backbone first to avoid edit collisions

## Question

Finding 5. `cli/measure_run.py` is 629 lines — the largest file in cli/ — and
`MeasureLoop.__init__` takes 9 positional params (measure_run.py:70-100) while
accumulating six responsibilities. The worst is `_handle_result`
(measure_run.py:510-628): a ~120-line block that does ROM write + summary write
+ OSError/`hard_failure`/`systematic_failure` classification + outcome append +
`collect` append.

Decision: extract `_handle_result` into a `ResultSink` collaborator owning the
ROM/summary write, the failure classification, and the outcome/collect append;
shrink `_measure_single` and `_measure_categorias` to thin callers. Leave the
config loop in `MeasureLoop`.

**Decided (approved):** (a) — extract `ResultSink`, no full decomposition.

## Answer

(to be appended on resolution)