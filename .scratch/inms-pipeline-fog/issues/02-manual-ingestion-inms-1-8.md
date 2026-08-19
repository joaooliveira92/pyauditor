# 02 — Manual-entry ingestion schema for INMS 1.8 desconformidades

**What to build:** a documented CSV schema for recording Anexo E occurrences by hand, since ticket 11's research found no primary source defining how a desconformidade técnica gets registered in a dataset (the real `/input/inms-001-08.csv` is empty — header only, same generic ITSM export used by unrelated indicators, not confirmed as the right format).

This ships an interim, human-fillable convention — not a claim that it matches whatever system IT eventually exports from. A fiscal técnico (or whoever logs occurrences today) needs *something* to fill in per competência; this ticket picks the simplest defensible shape and documents the choice as provisional.

**Blocked by:** None — can start immediately

**Status:** resolved

- [x] A CSV schema is defined for INMS 1.8: one row per occurrence, with an occurrence identifier column and a column listing the matched Anexo E code(s) (`OD-NN`, comma-separated for multi-enquadramento) — reusing the `external_catalog_sum` shape's existing `occurrence_id_column`/`catalog_codes_column` config fields, not inventing new engine behavior
- [x] The INMS 1.8 YAML config and its real `/input` acceptance_test are updated to point at this schema (still degenerate against the real empty file, per ticket 06 — that's unchanged)
- [x] A synthetic fixture with realistic occurrence data (multiple rows, at least one multi-code occurrence) proves the schema round-trips through `measure` into a correct ROM and JSON summary
- [x] The schema and its provisional status are documented in the config's comments and in `docs/spec/inms-pipeline.md` §11.3, explicitly flagged for revision if/when IT confirms a real export format
- [x] `mypy --strict` passes

## Answer

- **Schema:** one row per occurrence — `ID_Ocorrencia` (free identifier), `Data`, `Descricao` (free
  text, not consumed by the calculation — an audit trail for the fiscal técnico), `Codigos_Anexo_E`
  (one or more `OD-NN` codes, comma-separated for multi-enquadramento). Maps directly onto
  `external_catalog_sum`'s existing `occurrence_id_column`/`catalog_codes_column` config fields —
  zero engine changes, as scoped.
- `tests/fixtures/configs/inms-1.8.yaml` (the canonical config, still pointed at the real empty
  `/input/inms-001-08.csv`) updated: `occurrence_id_column`/`catalog_codes_column` now reference
  this schema's column names instead of the old, admittedly-wrong `"Nº Solicitacao"`/`"Atividades"`
  placeholders borrowed from the generic ITSM header. Since the real file has zero data rows, this
  is safe — Pydantic doesn't validate config field values against actual CSV headers, only YAML
  shape — and the comment explains why the schema and the real (still-empty) file don't need to
  agree yet. `acceptance_test` unchanged (still the degenerate 0-occurrence/0-point case from
  ticket 06).
- `tests/fixtures/manual_entry_examples/inms-1.8-{config.yaml,occurrences.csv}` (new) — a worked
  example with 5 realistic occurrences: a cabo-solto (`OD-52`, 100 pts), a multi-código occurrence
  (`OD-10,OD-20` → max-points-wins picks `OD-10`'s 500 over `OD-20`'s 50), a contribution-failure
  (`OD-30`, 500 pts), a deliberately incomplete row with no matched code (proves the quality gate
  rejects it, not silently drops it), and a planning-failure (`OD-60`, 200 pts). Total: 1300 points.
  `tests/test_manual_ingestion_inms_1_8.py` verifies the full round trip — quality-gate rejection,
  catalog lookup, max-points-wins dedup, total sum — and that the generated ROM correctly lists the
  rejection reason and the point breakdown. This CSV also serves as the documentation-by-example the
  ticket asked for: a fiscal técnico can copy its shape directly.
- `docs/spec/inms-pipeline.md` §11.3 gained a "Schema de preenchimento manual provisório" paragraph
  documenting the schema, explicitly framed as *not* an answer to the open ingestion-mechanism
  question — just a way to start recording occurrences while that question stays open — and pointing
  at the example fixture as the reference implementation.

Verified: `uv run mypy --strict src tests` → `Success: no issues found in 51 source files`. `uv run pytest -q` → `108 passed`. Manually rendered the example ROM — correctly shows the rejection row, the 4-occurrence point table, and `Σ Pontos_NMS = 1300`.
