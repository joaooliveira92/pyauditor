# 07 — YAML configs for the remaining `ratio` indicators (1.3–1.14)

**What to build:** one YAML config per remaining `ratio`-shaped indicator (1.3, 1.4, 1.5, 1.6, 1.7, 1.9, 1.11, 1.12, 1.13, 1.14), exercising all three `aggregation` variants the `ratio` shape supports (`count_distinct`, `sum`, `precomputed`), each carrying its own `acceptance_test` verified against the indicator's real `/input` CSV.

**Blocked by:** 02

**Status:** resolved

- [x] INMS 1.3 config uses `aggregation: sum` (razão de somas de dias, not distinct count) and its `acceptance_test` passes against `/input/inms-001-03.csv`
- [x] INMS 1.4, 1.5, 1.14 configs use `aggregation: precomputed` (numerator/denominator taken directly from the pre-aggregated monitoring-tool CSV, per spec.md §2.1) and their `acceptance_test`s pass against `/input/inms-001-04.csv`, `-05.csv`, `-14.csv`
- [x] INMS 1.6, 1.7, 1.9, 1.12, 1.13 configs use `aggregation: count_distinct` and their `acceptance_test`s pass against the corresponding real CSVs
- [x] INMS 1.11 config uses `target.operator: "<="` (inverted target direction) and its `acceptance_test` passes against `/input/inms-001-11.csv`
- [x] All 10 configs validate against the `RatioCalculation` Pydantic model with `mypy --strict` clean

## Answer

**This ticket also had to implement `sum` and `precomputed` aggregation** — ticket 02 deferred them
here on purpose, but the `RatioStrategy` only had `count_distinct` before this ticket:

- `pyauditor/config/models.py` — `RatioCalculation.aggregation` widened to
  `Literal["count_distinct", "sum", "precomputed"]`, with per-variant optional fields
  (`sum_numerator_column`/`sum_denominator_extra_column` for `sum`; `precomputed_result_column` for
  `precomputed`) and a `model_validator` enforcing the right fields are set for the chosen
  aggregation (Pydantic-layer validation, per spec §4). `numerator_filter` became optional (only
  required in practice for `count_distinct`).
- Two new `Filter` variants needed for real data shapes: `ColumnIn` (value ∈ a set — e.g. INMS
  1.11's `DESCONEXÃO` classification) and `DurationAtMost` (an `H:MM:SS` column ≤ N seconds — INMS
  1.12's 20-second threshold). `Filter` is now a 4-member value union.
- `pyauditor/engine/strategies/ratio.py` — `_aggregate()` dispatches on `aggregation`:
  `count_distinct` unchanged; `sum` sums two columns across all rows (`numerator = ΣDPE`,
  `denominator = ΣDPE + ΣDA`); `precomputed` asserts exactly one row and reads its percentage
  column directly, expressed as `(value, 100.0)` so the existing `numerator/denominator × 100`
  arithmetic reproduces it unchanged.
- `Penalty.base_points` gained a `0.0` default — only INMS 1.1 has a flat base in Anexo D; every
  other `ratio` indicator here is pure linear ("X pontos a cada Y% abaixo da meta", no base).
- **Bug fix (found while running 1.7 against real data):** `pipeline.load_rows` crashed on ragged
  rows — `/input/inms-001-07.csv` has free-text fields containing the `;` delimiter, which shifts
  columns and makes `csv.DictReader` stuff overflow into a `None`-keyed list. Fixed by only keeping
  the declared `fieldnames`, ignoring overflow.
- **Bug fix:** the CSV row-id column was hardcoded to `"Nº Solicitacao"` in `pipeline.py`, but INMS
  1.7's dataset uses `"Nº Ticket"`. Moved to `Source.id_column` (default `"Nº Solicitacao"`,
  overridden per-config where needed).

**Real-data modeling notes (documented in each fixture's comments):**

- **INMS 1.3, 1.9** — real `/input` CSVs are empty (header only), same fog class as 1.8/1.10.
  Degenerate real acceptance tests; the `sum` math is proven by a synthetic fixture instead.
- **INMS 1.4, 1.5, 1.14 (`precomputed`)** — one real data row each from the monitoring tool; used
  directly. 1.5 and 1.14 both show 0% real availability in the sample data (large real penalties),
  1.4 shows 95.01% (below its 99.5% meta).
- **INMS 1.6** — the real CSV has no "reaberto" (reopened-ticket) signal at all (no duplicate ticket
  IDs, no relevant column), so `ΣCR` can't be derived from production data — same class of gap as
  1.8's dataset schema. Modeled as "0 reaberturas assumed" (documented, not fabricated as a
  meaningful validation); the actual `ΣCA − ΣCR` subtraction is proven by a synthetic fixture.
- **INMS 1.7** — Anexo D's 5 satisfaction categories are enforced via a quality-gate `in_set` check;
  the real CSV turned out to have many ragged/malformed rows (see bug fix above) plus
  "Avaliação Automática" entries that aren't real user ratings — both get rejected by the gate, not
  counted. Real result: 40 genuine ratings, all positive, 100%.
- **INMS 1.11** — the real telephony CSV's `DESCONEXÃO` column has 4 values (`Caller`, `Agent`,
  `Timeout`, `Abandon`); `Timeout`/`Abandon` are read as abandoned calls. Plausible from the values
  observed but not confirmed by any primary source — same caveat class as 1.2's SLA substring match.
- **INMS 1.12** — real data: all 492 calls answered within 20s (trivial 100%, still a real result).
- **INMS 1.13** — Anexo D doesn't fix a numeric meta for this indicator ("será acordado com a
  CONTRATADA... revisão trimestral"); the config uses a documented `90.0` placeholder, flagged as
  needing confirmation from the contract manager before production use.

Verified: `uv run mypy --strict src tests` → `Success: no issues found in 30 source files`.
`uv run pytest -q` → `30 passed`. Also ran `pyauditor measure` against all 14 configs together
(this ticket's + tickets 02/04/05/06's) via the real CLI — all 14 ROMs generated; exit code 1 with
4 "falha de medição" errors for the indicators with empty real datasets (1.3, 1.8, 1.9, 1.10), as
expected and already documented per-indicator.
