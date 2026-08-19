# 03 — Manual-entry ingestion schema for INMS 1.10 security controls

**What to build:** the same treatment as ticket 02, for INMS 1.10's `QRC`/`QCSI` security-controls checklist. Ticket 05's implementation proved the `count_difference` math against synthetic data because the real `/input/inms-001-10.csv` is empty (same generic ITSM header, no signal for "recommended" vs. "implemented" controls).

**Blocked by:** None — can start immediately

**Status:** resolved

- [x] A CSV schema is defined for INMS 1.10: one row per recommended security control, with a control identifier column and an "implantado" S/N column — reusing the `count_difference` shape's existing `recommended_filter`/`implemented_filter` config fields
- [x] The INMS 1.10 YAML config and its real `/input` acceptance_test are updated to point at this schema (still degenerate against the real empty file, per ticket 05 — that's unchanged)
- [x] A synthetic fixture with a realistic control checklist (some implemented, some not) proves the schema round-trips through `measure` into a correct ROM and JSON summary
- [x] The schema and its provisional status are documented in the config's comments, explicitly flagged for revision if/when a real security-controls tracking system is identified
- [x] `mypy --strict` passes

## Answer

- **Schema:** one row per recommended control — `ID_Controle`, `Framework` (Anexo D says the
  security framework "será acordado com a CONTRATADA", so this column records whichever one gets
  agreed on, not a fixed value), `Descricao` (free text), `Implantado` (`S`/`N`). `QRC` = rows
  surviving the quality gates; `QCSI` = the `Implantado = S` subset — reusing
  `count_difference`'s existing `recommended_filter`/`implemented_filter` fields, zero engine
  changes.
- `tests/fixtures/configs/inms-1.10.yaml` (canonical, still pointed at the real empty
  `/input/inms-001-10.csv`) updated: `implemented_filter.column` changed from the old, wrong
  `"No prazo"` placeholder (borrowed from the generic ITSM header) to `"Implantado"`. Safe for the
  same reason as ticket 02 — the real file has zero rows, so no value depends on this match today.
  `acceptance_test` unchanged (still the degenerate 0/0/0 case from ticket 05).
- `tests/fixtures/manual_entry_examples/inms-1.10-{config.yaml,controles.csv}` (new) — a worked
  example with 6 controls (MFA, WAF, SIEM implemented; DLP, EDR not; network segmentation left
  blank to prove quality-gate rejection). `QRC=5`, `QCSI=3`, `CNI=2`, penalty 2000, 60% result,
  não conforme. `tests/test_manual_ingestion_inms_1_10.py` verifies the full round trip and that the
  ROM correctly shows the rejection reason and all 3 `count_difference` terms.
- `docs/spec/inms-pipeline.md` gained §2.2 documenting the schema and its provisional status,
  pointing at the example fixture, mirroring §11.3's treatment of INMS 1.8.

Verified: `uv run mypy --strict src tests` → `Success: no issues found in 52 source files`. `uv run pytest -q` → `110 passed`. Manually rendered the example ROM — correctly shows the rejection row and `QRC=5 / QCSI=3 / CNI=2`.
