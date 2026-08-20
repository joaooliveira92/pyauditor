# pyauditor

Monthly SLA measurement pipeline for the INMS indicators of contract 40/2022,
run separately for each contracting órgão (Ministério da Cultura and
Ministério do Turismo, Anexo D — Prazos e Níveis Mínimos de Serviço).

Given declarative `inms-<n>.yaml` + `inms-<n>.csv` pairs per órgão,
`pyauditor` runs the 14 contractual indicators through quality gates, writes
a Markdown memória de cálculo (ROM) per indicator, and consolidates
everything into an Excel report plus a contract cover sheet — one report per
órgão. A separate `consolidate` step fuses both órgãos' reports into the
contract's financial workbook (glosa, cálculo de pagamento).

See `docs/spec/inms-pipeline.md` for the full spec.

## Install

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

## Usage

Run `pyauditor` with no arguments for a guided, interactive flow that walks
through the whole competência (bootstrap → measure → report → consolidate),
tracks progress live, and offers retry/skip/abort on failure. It requires a
real terminal — piped/non-interactive input falls back to an error telling
you to use a subcommand directly.

Otherwise, four subcommands, meant to run separately so the fiscal técnico
can re-run `measure` as new CSVs arrive without redoing the whole month —
plus a fifth, `run`, that chains all four in one scriptable invocation.

`bootstrap`, `measure` and `report` take `--orgao {MinC,MTur,both}` (default
`MinC`); `both` runs each órgão sequentially, never crossing their data.
Configs live per órgão at `configs/<órgão>/`, data at
`input/<órgão>/<AAAA>/<MM>`, ROMs at `roms/<órgão>/<competência>/`, and each
órgão gets its own cover sheet (`capa_<órgão>.xlsx`) and report
(`reports/relatorio_<competência>_<órgão>.xlsx`).

```bash
# create each órgão's contract cover sheet (idempotent — skips existing files)
uv run pyauditor bootstrap --orgao both

# measure every configured indicator for a competência, per órgão
uv run pyauditor measure 2026-06 --orgao both --config-dir configs --data-dir input --output-dir roms

# consolidate each órgão's ROMs into its own Excel report
uv run pyauditor report 2026-06 --orgao both --roms-dir roms --output-dir reports

# fuse both órgãos' reports into the contract's financial workbook
uv run pyauditor consolidate 2026-06 --report-dir reports --roms-dir roms

# or, equivalently, chain all four steps in one non-interactive invocation
uv run pyauditor run 2026-06 --orgao both
```

`run` accepts the same `--orgao`/`--config-dir`/`--data-dir`/`--output-dir`/
`--capa-path`/`--final-month` flags as the individual subcommands, and skips
any step already `done` from a previous invocation — progress is tracked per
`(competência, órgão)` in `.pyauditor/runs/`, so a failed or interrupted run
can just be re-run to resume where it left off.

`measure` writes one `<indicator.id>.md` ROM and one `<indicator.id>.json`
summary per indicator config found in `--config-dir`. `report` reads the
JSON summaries, not the Markdown.

`consolidate` never re-runs `measure`/`report` — it requires both órgãos'
reports to already exist (erroring on whichever is missing) and writes
`reports/relatorio_<competência>_consolidado.xlsx` (`CAPA_E_CONTROLE`,
`SERVICOS_POR_ORGAO`, `INMS_BASE`, `GLOSAS`, `CALCULO_PAGAMENTO`). Re-running
it over an already-decorated consolidado preserves the fiscal's decision
columns (Justificativa / Decisão Fiscal / Observação) by
`(indicador, órgão)`, only refreshing the recomputed fields.

## Development

```bash
uv run pytest
uv run mypy
```

`mypy` runs in strict mode over `src` and `tests` (see `pyproject.toml`).
