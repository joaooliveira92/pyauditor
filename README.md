# pyauditor

Monthly SLA measurement pipeline for the INMS indicators of contract 40/2022
(Ministério da Cultura, Anexo D — Prazos e Níveis Mínimos de Serviço).

Given declarative `inms-<n>.yaml` + `inms-<n>.csv` pairs, `pyauditor` runs the
14 contractual indicators through quality gates, writes a Markdown memória de
cálculo (ROM) per indicator, and consolidates everything into an Excel
report plus a contract cover sheet.

See `docs/spec/inms-pipeline.md` for the full spec.

## Install

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

## Usage

Three subcommands, meant to run separately so the fiscal técnico can
re-run `measure` as new CSVs arrive without redoing the whole month.

```bash
# create the contract cover sheet (idempotent — skips if it already exists)
uv run pyauditor bootstrap --capa-path capa.xlsx

# measure every configured indicator for a competência
uv run pyauditor measure 2026-06 --config-dir configs --data-dir input --output-dir roms

# consolidate the month's ROMs into the final Excel report
uv run pyauditor report 2026-06 --capa-path capa.xlsx --roms-dir roms --output-dir reports
```

`measure` writes one `<indicator.id>.md` ROM and one `<indicator.id>.json`
summary per indicator config found in `--config-dir`. `report` reads the
JSON summaries, not the Markdown.

## Development

```bash
uv run pytest
uv run mypy
```

`mypy` runs in strict mode over `src` and `tests` (see `pyproject.toml`).
