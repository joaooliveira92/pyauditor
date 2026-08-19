# 01 — Repo scaffold & tooling

**What to build:** the package layout and toolchain the rest of the pipeline builds on — `src/pyauditor/{config,engine,rom,excel,cli}`, a `uv`-managed `pyproject.toml`, `mypy --strict` configured, Loguru wired for logging, and `pytest` runnable. No pipeline behaviour yet.

**Blocked by:** None — can start immediately

**Status:** resolved

- [x] `src/pyauditor/` exists with `config/`, `engine/` (with `strategies/` subpackage), `rom/`, `excel/`, `cli/` packages
- [x] `uv run mypy --strict src` passes with zero errors on the scaffold
- [x] `uv run pytest` runs green (even with zero or trivial tests)
- [x] Loguru is configured and importable from a shared logging module
- [x] `docs/spec/inms-pipeline.md` §9 layout matches what's on disk

## Answer

Scaffolded via `uv init --name pyauditor --package --python 3.12`, then built out `src/pyauditor/{config,engine/strategies,rom,excel,cli}` as empty packages (each with `__init__.py`) matching spec.md §9 exactly. Added `pydantic` and `loguru` as runtime deps, `mypy` and `pytest` as dev deps (all via `uv add`). `[tool.mypy] strict = true` and `[tool.pytest.ini_options]` added to `pyproject.toml`. Shared logger lives at `src/pyauditor/logging.py` (Loguru, stderr sink), imported by `pyauditor.__init__.main`. A trivial `tests/test_scaffold.py` proves pytest collection/execution works. Added `.gitignore` (was missing after `uv init`) covering `.venv/`, caches, and `input/` (git-ignored production PII data per spec.md §8).

Verified: `uv run mypy --strict src` → `Success: no issues found in 8 source files`. `uv run pytest` → `1 passed`. `uv run pyauditor` → runs and logs via Loguru.
