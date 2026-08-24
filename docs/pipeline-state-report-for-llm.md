# Pipeline de Aferição INMS — State Report (for an LLM)

> This document is written to hand off a complete mental model of the current
> pipeline to an LLM that will read it, understand it, and (if asked) safely
> maintain or evolve it. It describes **what exists today**, the contracts the
> code already respects, and — without prescribing a refactor — where the system
> is genuinely fragile and hard for a new maintainer to trust. It is descriptive,
> not prescriptive.

---

## 0. What this system is

`pyauditor` is a **government audit pipeline** for contract **40/2022** between
two public agencies — **MinC** (Ministry of Culture) and **MTur** (Ministry of
Tourism) — and an external contractor providing IT services.

The audit's purpose is to **verify whether the contractor actually delivered**
the service levels the contract demands. Every calendar month ("competência",
e.g. `2026-06`) the contractor hands over CSV extracts of their own systems.
The auditor's team uses `pyauditor` to:

1. Load the contractor's raw CSV data.
2. Push it through 14 **contractual indicators** (`INMS 1.1` … `INMS 1.14`) —
   each is an SLA rule (e.g. "≥98% of incidents resolved in time").
3. Compute, per indicator, a **score** and a **penalty in points** when the
   target is missed.
4. Write a **calculation memorandum (ROM)** per indicator — a Markdown "memória
   de cálculo" that documents exactly where each number came from.
5. Assemble a monthly **Excel report per agency**, then merge both into a
   **financial workbook** that computes the **glosa** (the monetary deduction
   to apply to the month's payment).

The output is a **reproducible, auditable assessment of a payment period** —
the auditor uses it as evidence in a financial decision against the supplier.

Two properties are load-bearing and unusual:

- **The audited party supplies the data.** There is no independent source of
  truth; the pipeline validates *structure* but ultimately trusts files whose
  content the contractor controls.
- **The deliverable is a legal/financial artifact.** The ROMs and the
  consolidated workbook are not internal diagnostics; they are the paper trail
  that justifies a monetary deduction.

---

## 1. The system's contract (inputs)

The system is **configuration-driven**. Two directories hold everything a
human operator must touch:

### `configs/` — the rules

- `configs/_shared/` — **single-source** canonical configs:
  - 14 files `inms-01.yaml` … `inms-14.yaml`, one per indicator. Each declares
    the indicator identity, the source dataset, the quality-gate checks, the
    calculation shape + target + penalty.
  - `datasets.yaml` — the **manifest**: maps human-readable dataset aliases
    (`incidentes`, `requisicoes`, …) to a real CSV filename + delimiter +
    encoding.
- `configs/<agency>/` — per-agency overrides:
  - `categorias.yaml` — maps business **Categorias** (e.g. "Atendimento Remoto
    aos Usuários") to literal `Grupo_executor` values in the raw CSV, per INMS.
  - Some agencies also carry **per-agency `inms-*.yaml`** that override the
    base shape (e.g. MTur splits INMS 1.1/1.2/1.3/1.6/1.7 into per-N1/N2/N3
    YAMLs, MinC does not).

### `input/` — the data (git-ignored, contains PII)

- `input/<agency>/<YYYY>/<MM>/inms-<nn>.csv` — one raw extract per indicator,
  per agency, per month. Real names / requesters / technicians / PII live here.
- Top-level contract-side files: `capa*.csv`, `equipe.csv`, `objetos.csv`,
  `prazos.csv`, `localidades.csv`, `perfis_professional.csv`, `sansoes.csv` —
  hand-fill forms or genuinely tabular contract data, stay CSV. Static
  contract reference data with no in-pipeline writer —
  `dados_contratuais.yaml`, `ajuste_inms.yaml`, `desconto_regulatório.yaml`
  — moved to YAML: shaped as field/value or formula/text, not rows.

> Because `input/` is git-ignored, the repo is not self-contained: a fresh
> maintainer cannot reproduce a month without the production files. Tests use
> synthetic fixtures only.

---

## 2. The pipeline phases

The CLI exposes six subcommands. `run` chains five of them into one invocation.

```
bootstrap ──> split ──> measure ──> report ──> consolidate
```

| Phase | What it does | Output |
|---|---|---|
| `bootstrap` | creates cover sheets (`capa.csv`, `capa_<agency>.csv`) and the team skeleton | CSV cover sheets |
| `split` | validates `categorias.yaml` + raw CSVs, filters rows per Categoria | `sintetico.xlsx`; optionally materialized `_split/*` |
| `measure` | computes the competence indicators, one ROM per indicator | `roms/<agency>/<comp>/<inms>.md` + `.json` |
| `report` | consolidates the ROMs into the agency's report workbook | `reports/relatorio_<comp>_<agency>.xlsx` |
| `consolidate` | merges both agencies' reports into the financial workbook | `reports/relatorio_<comp>_consolidado.xlsx` |

`run` is **resumable**: it persists done-stage state to `.pyauditor/runs/`
(git-ignored) and skips finished stages on a re-run (`report`/`consolidate`
always regenerate). `--force` reprocesses everything; `--clean` deletes
`roms/`+`reports/` first; `--on-warning pause` stops at each stage that ends
with warnings.

---

## 3. The measurement engine

Every indicator flows through one backbone (`engine.pipeline.measurement_source`):

```
load YAML config ──> resolve source (manifest) ──> detect delimiter ──>
read raw CSV ──> validate referenced columns exist in header ──>
  filter rows to competence period window ──> run quality gates ──>
    dispatch to shape strategy ──> produce CalculationResult
```

### Three layers of validation, not two

- **Pydantic config validation** (`config/models.py`): is the YAML itself
  well-formed and self-consistent? Frozen, strict, `extra='forbid'`. Uses a
  **discriminated union on `shape`** so a `ratio` config can never accidentally
  be handed to a `segmented_ratio` strategy.
- **Column-existence check** (`_validate_columns`): every column the YAML
  references must exist in the real CSV header. Downgraded to a warning when
  the CSV is legitimately empty that month.
- **Quality gates** (`engine/quality_gates.py`): per-row *data* checks — a
  column not-null, a column in a set. Produces an `accepted` / `rejected` list
  that feeds the ROM.

### Five calculation shapes

| Shape | Indicators | Semantics |
|---|---|---|
| `ratio` | 1.1, 1.3, 1.6, 1.7, 1.11, 1.12 | numerator/denominator ×100 vs target; linear penalty in steps |
| `segmented_ratio` | 1.2 | 3 sub-ratios (Alta/Média/Baixa), each with own target and step points; penalty = sum |
| `count_difference` | (available, unused) | difference of two filtered counts |
| `external_catalog_sum` | (available, unused) | sum points from Anexo E catalog |
| `precomputed_table` | 1.4, 1.5, 1.8, 1.9, 1.10, 1.13, 1.14 | each row already carries its computed result; pipeline sums |

`ratio` itself has three aggregation modes: `count_distinct`, `sum`, and
`precomputed` — each with its own field contract (sum has *exactly one* of
`sum_denominator_extra_column` / `sum_numerator_subtract_column`, enforced by
validator).

### Scoring + penalty + glosa (the money)

- **Per-indicator**: target operator/value + penalty (base + linear steps) →
  "pontuación apurada".
- **GLOSA** (`excel/glosas.py`): `Ajuste_NMS(%) = min(30%, Σ Points × 0.001%)`,
  applied to the monthly base value. A hard-coded **30% cap** and **rollover**
  of any excess to next month (except the final contract month). A separate
  **reincidencia** rule: cap breached 3+ times in a 6-month window flags partial
  non-performance (compliance flag, does not change the amount).
- **Rateio MinC/MTur**: payment split is hard-coded `RATEIO_PADRAO = 0.5`
  (marked *provisional* until an official source exists).
- The **cross-agency split** in the consolidated workbook is computed
  proportional to each agency's points.

### Heuristic failure classification (a fragile seam)

`MeasurementResult` distinguishes:

- `hard_failure` — quality gates rejected every row that existed.
- `systematic_failure` — calculation ran but looks structurally broken, decided
  by a heuristic: **non-conforming AND result_pct ≈ 0% AND rows were accepted**
  (with a carve-out for non-percent precomputed shapes). This is a reasonable
  guess, but it is a *guess* — downstream human judgment must confirm it.

---

## 4. Output artifacts (the audit record)

1. **ROMs** (`roms/`) — one Markdown per indicator×competence (or per
   category/asset when segmented). Sections: Identificación, Líneas aprobadas
   por el quality gate, Rechazos, Memoria de cálculo, Resultado vs meta,
   Responsables. Provenance (input file SHA-256, delimiter, encoding, config
   hash, pipeline version) is captured in the ROM — this is the core of
   auditability.
2. **Sidecar JSON** (`roms/.../*.json`) — structured summary per ROM; the
   report phase reads these, not the Markdown prose.
3. **Per-agency report workbook** (`reports/relatorio_<comp>_<agency>.xlsx`).
4. **Consolidated financial workbook** (`reports/relatorio_<comp>_consolidado.xlsx`)
   — sheets: `CAPA_E_CONTROLE`, `SERVICIOS_POR_ORGAO`, `INMS_BASE`,
   `GLOSAS`, `CALCULO_PAGAMENTO`, plus a grouped INMS base.

---

## 5. Supportability and fragility (the part to read twice)

This section is a diagnosis, ordered roughly by how much it hurts a new
maintainer. It does **not** recommend a specific rewrite.

### 5.1 The audit trusts the audited party's data with only shallow checks

The heaviest structural risk. The contractor is both the data producer and the
subject. The pipeline checks:

- that referenced columns exist in the header;
- `not_null` / `in_set` on a couple of columns;
- delimiter auto-detection against the declared manifest.

It does **not** verify *identity* (this is the real person/request), *consistency*
across files, totals reconciliation, or cross-agency plausibility. A contractor
could silently change a column meaning, add/remove rows, or reformat a date and
the pipeline would either warn-and-continue or fail with a generic error. For a
**financial deduction**, that is a wide, unguarded boundary. Any maintainer
touching data loading should treat "the file is authoritative" as a risk to
manage, not an assumption.

### 5.2 Delimiter and schema inference is heuristic, and silent degradation

`_detect_delimiter` guesses `,` vs `;` from a header + 20-row sample, and when
ambiguous it **warns and keeps the configured value**. A wrong guess produces
silently misparsed rows (dates shifted, columns merged). For an audit this is
exactly the failure mode that changes the answer without leaving a trace. The
`ragged_rows` counter exists to surface it, but it is only counted, not
fail-closed.

### 5.3 Business rules live in *two* places

The contract's math is split between:

- **declarative YAML** (targets, penalties, shapes, gates), and
- **imperative Python** (the penalty formula in `ratio.py`, the glosa formula
  in `glosas.py`, the `RATEIO_PADRAO`, the reincidencia window, the systematic
  failure heuristic).

To answer "what is the rule for INMS 1.3?" a maintainer must look in both
places and infer how they compose. The "configuration" is not a complete
expression of the contract; it is a partial one with the rest in code. This
makes the audit logic non-trivial to re-verify from first principles.

### 5.4 Configuration is a "single source" that is not single

`configs/_shared/` is called single-source, but `configs/<agency>/` carries
both per-agency `categorias.yaml` *and* per-agency `inms-*.yaml` overrides.
Discovery (`discover_config_files`) walks `*.yaml`, skips `datasets.yaml`,
injects the agency scope for `_shared`, and *errors* when a per-agency config
declares the wrong agency. In practice the set of indicators per agency is
**not identical** (MTur splits more indicators per-level; MinC does not). The
schema that says "single source of truth" coexists with real per-agency drift —
a subtle thing a new maintainer will not expect and may trust too much.

### 5.5 The resume/force/clean state machine is a support burden

`.pyauditor/runs/`, done-stages, resume-on-re-run, `--force`, `--clean`,
`--on-warning pause`. This machinery exists to compensate for a pipeline that
is only *partially* idempotent (`report`/`consolidate` always rerun; other
stages only if not marked done). It is correct and documented, but it is a lot
of context. The single biggest support risk: an operator re-runs after editing
an input and *thinks* a stage reprocessed when the resume state silently kept
a stale `done` marker. The documentation calls this out; new operators will
still trip on it.

### 5.6 Multi-agency, multi-init, multi-stage, multi-shape cross product

The real complexity is combinatorial: 2 agencies × 14 indicators × multiple
shapes × some shapes per-asset × per-category segmentation × per-competence
folders × report+consolidate+glosa+history. Any single piece is simple; the
**system as a whole** is a lot of interacting vocabulary. The glossary
(`CONTEXT.md`) and spec (`docs/spec/inms-pipeline.md`) exist precisely because
this vocabulary is dense. A new maintainer's first two weeks will be learning
the words, not the code.

### 5.7 Language / comment fragmentation

The codebase mixes three languages: README/docs in English, most comments and
all domain docstrings in **Portuguese**, and *some* code comments in
**Spanish** (e.g. `categoria_filter.py`'s `RawCsv` docstring, "encida",
"fila", "encabezado"). This is a maintainability tax: identifiers and
`log_event` messages are a mix of PT and ES, so searchability suffers and a
single-language-speaking maintainer cannot reliably grep. Not a correctness
issue, but a real onboarding cost.

### 5.8 Deep Excel/OpenPyXL surface

The workbook builders (`excel/`) are extensive and hand-assembled with
openpyxl — cover sheets, styles, verbatim CSV blocks, grouped INMS bases,
decision-column readback. Verifying a workbook's layout by reading the code
is slow. These are the most fragile files to modify without a diff on the
generated artifact.

### 5.9 Testing is strong, but boundary-light

The suite is serious: branch coverage ≥90%, hypothesis, property-based,
synthetic per-shape fixtures. But because production data is git-ignored and
the real risk is **contraductor drift** (5.1), the highest-value tests (schema
drift, delimiter surprises, malformed date formats, contractor renaming a
column) are exactly the ones least covered by synthetic fixtures. The tests
prove the engine does what the YAML says; they cannot prove the YAML matches
the contractor's *real* monthly export.

### 5.10 Hardcoded financial parameters

The 30% cap, the 0.001 points-to-percent, the 6-month window, the 3-strike
reincidencia threshold, and the 0.5 provisional rateio are all literals in
code with `Final` annotations. A contract renegotiation means a code change,
and code changes to the money path need a reviewer who can trace a number from
CSV → ROM → glosa. Not wrong, but it means the "configuration" layer does not
contain the *most* sensitive business numbers.

---

## 6. What is already solid (don't break these)

- **Immutable, strict Pydantic config** with a shape discriminator. The
  "broken config" vs "rejected data" split is real and well-separated.
- **Single backbone** (`measurement_source`) now shared by measure/split/
  sintetico — this eliminated a historical set of 4 parallel reimplementations.
- **Explicit provenance** captured in each ROM (file hash, delimiter, encoding,
  config hash, pipeline version). This is the backbone of defensibility.
- **Synthetic, never real-PII fixtures**; data dirs git-ignored.
- **Documentation density**: spec, glossary, ADR dir, styleguide. The system
  is unusually well-documented for its size — a new maintainer has a real
  entry point.
- **Deterministic, resumable, scriptable CLI** with structured logs and JSON
  summaries suitable for automation.

---

## 7. The one-paragraph mental model

`pyauditor` turns the contractor's monthly CSVs into a legally-usable answer
to "did they hit the SLA, and how much do we dock?" It does this through a
declarative, config-driven engine (5 shapes, 14 indicators, 2 agencies) that
produces an auditable paper trail (ROMs → per-agency workbooks → a consolidated
financial workbook with a capped, rollover glosa). Its strongest assets are
the typed config contract, the shared measurement backbone, the provenance
capture, and the documentation. Its fragilities are the ones inherent to
**auditing data the audited party supplies** — shallow schema trust, guessed
delimiters, business math split between YAML and code, provisional hardcoded
financial constants, and a resume-state machine that can quietly skip
reprocessing. Anyone maintaining it should first understand the vocabulary in
`CONTEXT.md`, then treat the data boundary as the risk it is, and never change
the money path without re-verifying a number end-to-end.