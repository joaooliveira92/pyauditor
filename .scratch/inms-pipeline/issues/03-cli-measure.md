# 03 — CLI `measure` subcommand

**What to build:** `pyauditor measure <competência>` runs the pipeline built in ticket 02 for a configured indicator and writes its ROM Markdown to disk, so a fiscal técnico can invoke the pipeline from the command line instead of a test harness.

**Blocked by:** 02

**Status:** resolved

- [x] `pyauditor measure <competência>` discovers configured `ratio`-shaped indicators (at minimum INMS 1.1), runs the pipeline per indicator, and writes one ROM Markdown file per indicator to a configurable output directory
- [x] Rerunning `measure` for the same competência overwrites the prior ROM (measure is idempotent per indicator/competência, not cumulative)
- [x] Command exits non-zero if any indicator's quality gates produce a hard failure (per spec §4), and the failure is visible in the CLI output, not just buried in the ROM
- [x] `mypy --strict` passes on `cli/`

## Answer

- `pyauditor/engine/pipeline.py` gained `discover_configs(config_dir)` (globs `*.yaml`, loads each via Pydantic) and `MeasurementResult.hard_failure` — a property, true when `quality_gate_report.accepted` is empty (no rows survived the quality gates, so there's nothing left to measure). This is the concrete definition adopted for "hard failure" per spec §4 — not specified further by the wayfinder decisions, so it's the narrowest reading: a measurement that produced literally no data to compute against.
- `pyauditor/cli/measure.py` — `run_measure(competencia, config_dir, data_dir, output_dir)` discovers configs, runs `measure()` per indicator, writes `<output_dir>/<competencia>/<indicator.id>.md` (always — even on hard failure, so the rejection detail is visible in the ROM, not just the CLI log), logs one line per indicator via Loguru (`logger.error` on hard failure, `logger.info` otherwise), and returns `1` if any indicator hard-failed, else `0`.
- `pyauditor/cli/main.py` — `argparse`-based entry point with a `measure` subcommand (`competencia` positional + `--config-dir`/`--data-dir`/`--output-dir`, defaulting to `configs`/`input`/`roms`); `bootstrap`/`report` are left as a docstring note for tickets 08-09, not stubbed out.
- `pyauditor/__init__.py`'s `main()` now dispatches to `cli_main()` (replacing the ticket-01 placeholder "scaffold ready" log) and `sys.exit`s with its return code — `pyauditor measure ...` is a real, installed console script now.
- Idempotency verified by running `measure` twice with different underlying CSV data for the same competência and asserting the ROM's content changes to match the second run, not the first (no accumulation).
- Hard-failure path verified with a synthetic config/CSV where every row fails a `not_null` check; asserts exit code `1` and that the ROM is still written.
- Manually verified via the installed `pyauditor` console script against the real INMS 1.1 fixture + `/input/inms-001-01.csv`, from a directory outside the repo, confirming the CLI (not just the test harness) works end-to-end.

Verified: `uv run mypy --strict src tests` → `Success: no issues found in 20 source files`. `uv run pytest -q` → `6 passed`.
