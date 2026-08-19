# 08 — CLI `bootstrap` subcommand

**What to build:** `pyauditor bootstrap` creates the contract's Excel capa (`CAPA_E_CONTROLE` tab — gestor, SEI, empresa, CNPJ, competência, etc.) if it doesn't already exist. Must be idempotent: rerunning it when the file exists is a no-op, never a silent overwrite.

**Blocked by:** 01

**Status:** resolved

- [x] `pyauditor bootstrap` creates the Excel capa workbook with the `CAPA_E_CONTROLE` tab and the fields listed in `docs/spreadsheet.md` §Aba 1, if the target file does not exist
- [x] Rerunning `pyauditor bootstrap` when the file already exists makes no changes to it and exits cleanly (not an error, not a silent overwrite)
- [x] `mypy --strict` passes on `excel/` and `cli/`

## Answer

- `pyauditor/excel/capa.py` — `build_capa_workbook()` (pure, in-memory) builds the `CAPA_E_CONTROLE` sheet with all 19 fields from `docs/spreadsheet.md` §Aba 1 (número do contrato through situação geral da aferição) as label/value rows, plus the 8-option "Situações possíveis" as an Excel data-validation dropdown on the situação cell (defaulted to "Em preenchimento", the first option). Basic formatting per `docs/styleguide.md` (Arial 10 body, bold title/headers, dark header fill with white text, gridlines hidden, thin bottom borders as row separators, no decorative styling) — light-touch since this is a single label/value tab, not a financial schedule.
- `bootstrap_capa(path)` — the idempotency contract: returns `False` and touches nothing if `path.exists()`; otherwise creates parent directories and writes the workbook, returns `True`.
- `pyauditor/cli/bootstrap.py` — `run_bootstrap(capa_path)` wraps `bootstrap_capa` with OSError handling (spec §6 CLI error-visibility pattern, matching `cli/measure.py`), logs whether it created or found-existing, returns 0/1.
- `pyauditor/cli/main.py` — wired the real `bootstrap` subcommand (was a `parser.error("não implementado")` stub), with `--capa-path` defaulting to `capa.xlsx` in the working directory (no established convention existed for this path; documented as the default, overridable).
- Updated `tests/test_cli_main.py`'s obsolete "`bootstrap` exits 2" test (from when it was unimplemented) to verify the real dispatch — both the `--capa-path` override and the default path — since that assertion was superseded by this ticket's own scope, not by drift.

Verified: `uv run mypy --strict src tests` → `Success: no issues found in 39 source files`. `uv run pytest -q` → `63 passed`. Manually ran the installed `pyauditor bootstrap` CLI twice against a fresh path — first run creates the workbook with all 19 fields and the situação dropdown defaulted correctly; second run is a true no-op (logs "já existe", `mtime` unchanged).
