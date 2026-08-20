Type: research
Status: resolved

## Question

Review `src/pyauditor/config/` (`manifest.py`, `catalog.py`, `models.py`) against the `python-production-engineer` skill's checklist (`.agents/skills/python-production-engineer/SKILL.md`). Read every file in the package in full before writing findings — no skimming the largest file and stopping.

Judge specifically:

- Typing strictness (`mypy --strict` already gates this repo — note anything the type checker can't catch: `Any` leaking across a public boundary, loose `dict`/`str` where a domain type belongs).
- Error handling at the config/YAML parsing boundary — are malformed inputs caught with actionable messages, or do they raise cryptic library exceptions? Any bare `except Exception`?
- Validation: are external inputs (YAML files, manifest entries) validated at the boundary before flowing into `engine/`?
- Primitive obsession: raw dicts/strings standing in for a domain concept that deserves its own type.
- Test coverage: does `tests/test_catalog.py` / `tests/test_config_per_orgao.py` / relevant tests actually exercise the failure paths, or only the happy path?

Report each finding as `file:line — severity — description — suggested fix`, ordered by the skill's priority list (correctness/data-loss first, style last). Skip anything ruff/mypy already enforces clean (verify with `uv run ruff check src/pyauditor/config` and `uv run mypy src/pyauditor/config` first, note the baseline, then don't re-report what's already clean).

## Answer

**Tooling baseline** (run 2026-08-20):
- `uv run ruff check src/pyauditor/config` — 9 findings, all style/modernization noise already caught by the linter: `UP035` (import `Mapping` from `collections.abc`, `catalog.py:11`, `manifest.py:12`), `UP040` (`TypeAlias` → `type` keyword, `models.py:101,144,231,318`), `E501` (line too long, `models.py:136`), `RUF003` (ambiguous minus sign in comments, `models.py:156-157`). Not re-reported below.
- `uv run mypy src/pyauditor/config` — `Success: no issues found in 4 source files` (repo runs `strict = true`). Not re-reported below.

Read in full: `catalog.py` (106 lines), `manifest.py` (102 lines), `models.py` (359 lines, all 4 indicator shapes + acceptance-test models). Cross-checked against `tests/test_catalog.py` and `tests/test_config_per_orgao.py`, and grepped the whole tree for any other manifest/DatasetEntry test.

Findings, ordered by the skill's priority list:

1. **`src/pyauditor/config/manifest.py:75` and `src/pyauditor/config/catalog.py:75`** — correctness / error handling (priority 1 & 6) — `yaml.safe_load(text)` is called with no `try/except` around malformed YAML syntax. Confirmed by reproduction: a syntax error (e.g. unclosed `[`) makes a raw `yaml.parser.ParserError` propagate uncaught out of both `load_manifest()` and `load_anexo_e_catalog()`, bypassing the actionable `ValueError` wrapping both functions otherwise provide for shape/validation errors (`_load_raw`'s `isinstance` checks, `ValidationError` → `ValueError` translation). This is exactly the "malformed input raises a cryptic library exception instead of an actionable message" failure mode the skill flags — a user who fat-fingers `datasets.yaml` gets a pyyaml traceback with a `<unicode string>` label instead of "malformed YAML in `datasets.yaml`: ...". **Fix**: wrap the `yaml.safe_load` call in both files in `try/except yaml.YAMLError as exc: raise ValueError(f"malformed YAML in {path}: {exc}") from exc` (or equivalent for the packaged catalog).

2. **`src/pyauditor/config/manifest.py:34-36`** — correctness / validation-at-boundary (priority 1) — `DatasetEntry.file`, `delimiter`, `encoding` are plain `str` with no `Field(min_length=1)`, unlike every other string field in the package (`models.py`'s `Source.delimiter`/`encoding`/`id_column` all use `min_length=1`, as does `CatalogItem`). Confirmed: `DatasetEntry(file="", delimiter="", encoding="")` validates successfully. An empty `file` then flows into `engine/pipeline.py:108`'s `data_dir / entry.file`, which evaluates to `data_dir` itself (a directory) — silently swapping "missing filename" for "confusing I/O error reading a directory as CSV" several layers downstream instead of failing at the config boundary with a clear message. **Fix**: add `Field(min_length=1)` to all three `DatasetEntry` fields, matching the `Source` model's convention.

3. **`src/pyauditor/engine/pipeline.py:108,112`** (consumer of `config/manifest.py` and `config/models.py`) — security / path handling (priority 2) — `data_dir / entry.file` and `data_dir / source.csv` are not validated against path traversal or absolute-path override. `Path.__truediv__` with an absolute right-hand side discards the left side entirely (`Path("/data") / "/etc/passwd" == Path("/etc/passwd")`), and `../` segments are not rejected. Today `datasets.yaml`/indicator YAMLs are trusted, version-controlled config, so exploitability is low, but the skill's "validar e normalizar entradas; restringir acesso a arquivos" applies at the config boundary where `file`/`csv` are declared (`manifest.py`, `models.py:72`), not just at the consumption site. **Fix**: validate `file`/`csv` reject absolute paths and `..` segments via a Pydantic field validator in `DatasetEntry` and `Source`, or resolve-and-check-`is_relative_to(data_dir)` at the point of use.

4. **`src/pyauditor/config/manifest.py`** — tests missing (priority 6) — there is no test file for `manifest.py` at all (grepped `load_manifest`/`DatasetManifest`/`DatasetEntry` across `tests/`: zero hits outside `src/`). None of its failure paths are exercised: malformed YAML (see finding 1), missing `datasets` key, non-dict `datasets` value, non-string alias, invalid `DatasetEntry` (triggers the `ValidationError`→`ValueError` wrap at `manifest.py:87-88`), unknown-alias `KeyError` from `DatasetManifest.resolve` (`manifest.py:59-66`), or the `lru_cache` behavior itself. Contrast with `catalog.py`, which has 5 tests covering exactly these shapes (`tests/test_catalog.py`). **Fix**: add `tests/test_manifest.py` mirroring `test_catalog.py`'s structure — one test per raised exception path, plus a happy-path resolve/alias test.

5. **`src/pyauditor/config/catalog.py:89-92`** — clarity/maintenance (priority 8) — `load_anexo_e_catalog`'s docstring says `Raises: ... ValidationError: if any item fails Pydantic validation`, but the implementation (`catalog.py:99-102`) catches `ValidationError` and re-raises `ValueError` — `ValidationError` never actually propagates to the caller. The docstring documents an exception type the function cannot raise. **Fix**: drop the `ValidationError` line from the docstring (only `RuntimeError`/`ValueError` are actually raised).

6. **`src/pyauditor/config/manifest.py:39-40`** — clarity/dead code (priority 8) — `class _RawManifest(dict[str, object])` is defined but never used anywhere in the file (or elsewhere); `_load_raw`'s actual return type is `Mapping[str, DatasetEntry]`, built via a plain `dict[str, DatasetEntry]`. Ruff's default rule set doesn't flag unused class definitions (only unused imports), so this survived the lint baseline. **Fix**: delete `_RawManifest`, or if it was meant to type the raw YAML mapping before validation, actually use it in `_load_raw`'s signature/body.

7. **`src/pyauditor/config/manifest.py:73-77`** — minor inconsistency, error handling (priority 6, low severity) — `_load_raw`'s `path.read_text(...)` lets a bare `FileNotFoundError` propagate with no added context (just the OS message + path), whereas `catalog.py:59-69`'s equivalent read wraps `OSError` in a `RuntimeError` with an explicit "failed to read packaged catalog ..." message. `load_manifest`'s docstring does document `FileNotFoundError` as intentional API surface, so this is a stylistic/consistency gap between the two loaders in the same package rather than a bug. **Fix (optional)**: either document why the two loaders differ, or align them (wrap with context in both, or neither).

No primitive-obsession findings beyond what's already noted above (2) — the package otherwise consistently uses frozen, strict, `extra="forbid"` Pydantic models in place of raw dicts, including discriminated unions for the four indicator shapes and acceptance-test expectations; that part of the design already matches the skill's "tipos de dominio em vez de dicionarios soltos" guidance well.
