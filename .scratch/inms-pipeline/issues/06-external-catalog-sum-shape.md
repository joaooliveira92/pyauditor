# 06 — `external_catalog_sum` shape + Anexo E catalog (INMS 1.8)

**What to build:** the fourth calculation shape — a linear sum of points from the 106-item Anexo E catalog (`OD-01`..`OD-106`), with the max-points-wins dedup rule when an occurrence matches multiple catalog items, and no cap or reincidência multiplier.

Per spec.md §11.3, the dataset ingestion schema for INMS 1.8 is explicitly unresolved fog — the real-world CSV format is unconfirmed. This ticket does **not** solve CSV ingestion for 1.8; it accepts a caller-supplied list of catalog occurrences (already matched to `OD-NN` codes) as input to the calculation, deferring the "how do occurrences get identified from raw data" question.

**Blocked by:** 02

**Status:** resolved

- [x] The 106-item Anexo E catalog is modeled as fixed Pydantic data (id, categoria, descrição, referência/unidade, pontuação), loaded from a config file, not derived at runtime from the Anexo D HTML
- [x] `ExternalCatalogSumCalculation` Pydantic model exists, discriminated on `shape: "external_catalog_sum"`, taking a list of occurrences (each referencing one or more catalog item ids)
- [x] `external_catalog_sum` strategy sums points linearly, applying max-points-wins when an occurrence matches multiple catalog items, with no cap
- [x] ROM renderer for `external_catalog_sum` lists occurrences with their matched catalog item, description, and points, per spec.md §7.2
- [x] A synthetic fixture (not the real, empty `/input/inms-001-08.csv`) exercises the dedup rule and the sum
- [x] `mypy --strict` passes on the new strategy module

## Answer

- **Catalog extraction:** parsed all 106 rows of Anexo E's Tabela 29 programmatically (regex over
  `docs/termo_de_referencia/anexo_e_desconformidade_tecnica.html`, not hand-typed) into
  `src/pyauditor/config/catalogs/anexo_e.yaml` — verified 22 categories and a 50–20.000 point range,
  matching ticket 11's research. `pyauditor/config/catalog.py`'s `load_anexo_e_catalog()` (Pydantic
  `CatalogItem`, `lru_cache`d) loads it as `dict[OD-NN, CatalogItem]`.
- `pyauditor/config/models.py` — `ExternalCatalogSumCalculation` (`shape:
  "external_catalog_sum"`, `occurrence_id_column`, `catalog_codes_column`,
  `catalog_codes_separator`), 4th member of the `Calculation` discriminated union. Per the ticket's
  scope note, this doesn't solve ingestion — each CSV row is assumed to already carry its matched
  Anexo E code(s) in `catalog_codes_column` (comma-separated for multi-enquadramento), so the
  existing row-based pipeline interface didn't need to change.
- **`target` and `penalty` became `Target | None` / `Penalty | None` on `IndicatorConfig`** (were
  required before): `external_catalog_sum` has no percentage meta per spec §11.2 (Anexo E is a
  linear point sum, not a ratio against a target). Added `assert config.target is not None` to
  `ratio.py` and `segmented_ratio.py`, which do require it.
- `pyauditor/engine/strategies/external_catalog_sum.py` — `ExternalCatalogSumStrategy` parses each
  row's codes, looks each up in the catalog, applies max-points-wins when a row's codes span
  multiple items (unmatched/unknown codes are silently skipped, not a hard failure), sums points.
  `conforms = total_points == 0`; `result_pct` is a nominal `0.0` (shape has no percentage meta).
  Registered in `SHAPE_REGISTRY["external_catalog_sum"]`.
- `pyauditor/rom/render.py` — `render_external_catalog_sum_memoria` (occurrence/item/descrição/pontos
  table + Σ line, matching spec §7.2's example almost exactly). The generic template's "Resultado
  vs meta" section now branches on `config.target is None`, rendering "Meta: não aplicável (soma de
  pontos, ver Anexo E)" instead of a percentage line for this shape.
- **Same dataset-ingestion fog as INMS 1.10 (ticket 05):** `/input/inms-001-08.csv` is empty — header
  only, already flagged in ticket 11. Its acceptance test is therefore degenerate (0 occurrences, 0
  points) and only proves the pipeline runs against the real file. The actual sum + max-points-wins
  dedup logic is proven by synthetic fixtures: `OD-52` (100) + `OD-01` (20.000) + max(`OD-02`=5000,
  `OD-03`=3000) → 5000, unmatched/empty codes skipped, total 25.100.

Verified: `uv run mypy --strict src tests` → `Success: no issues found in 29 source files`.
`uv run pytest -q` → `18 passed`.
