Type: research
Status: resolved

## Question

Review `src/pyauditor/cli/` (`main.py`, `bootstrap.py`, `measure.py`, `report.py`, `consolidate.py`, `run.py`, `dependencies.py`, `results.py`) against the `python-production-engineer` skill's checklist (`.agents/skills/python-production-engineer/SKILL.md`). Read every file in the package in full before writing findings.

Judge specifically:

- Duplicated Code: `bootstrap.py`/`measure.py`/`report.py`/`consolidate.py` each hand-roll an `_error(message)` closure that logs and builds an error-status Result dataclass with the same shape. Is this a real extraction opportunity (a shared `build_error_result` helper) or load-bearing per-dataclass duplication (each `Result` type has different fields, so a generic helper would need `**kwargs` and lose type safety)? Give a concrete recommendation either way.
- `main.py`'s size and responsibility — it now handles argument parsing, per-órgão fan-out, dependency pre-flight checks, and dispatch for 5 subcommands in one file. Divergent Change risk: does it change for multiple unrelated reasons? Would splitting per-subcommand dispatch into their own functions (already partially done via `_extract_*_request` helpers) reduce that, or is the current shape fine at this size?
- Error handling: every `run_*` function catches `OSError`/`(OSError, ValueError)`/etc. at specific points — is there a case where an unexpected exception type could still leak past the CLI boundary uncaught (check the `except Exception` in `measure.py` specifically — is the comment justifying it still accurate)?
- Security: `_run_log_path`/output paths built from `competencia`/`orgao` — any unsanitized user input reaching a filesystem path (cross-check against `measure.py`'s `_sanitize_indicator_id`, which does sanitize — is the same sanitization applied everywhere a user-influenced string becomes a path segment)?
- `cli/dependencies.py`'s registry — Middle Man risk (does it earn its place, or just forward to the four `check_*_ready` functions with no added logic)?

Report each finding as `file:line — severity — description — suggested fix`, ordered by the skill's priority list. Run `uv run ruff check src/pyauditor/cli` and `uv run mypy src/pyauditor/cli` first, note the baseline (this package has 4 known pre-existing ruff findings in `main.py` — `UP040`×2, `UP047`, one `E501` — don't re-report those unless they compound into something worse), don't re-report what's already clean.

## Answer

### Baseline tooling

- `uv run ruff check src/pyauditor/cli` — 4 findings, all pre-existing/expected: `UP040`×2 (main.py:37, main.py:39, `TypeAlias` vs `type`), `UP047` (main.py:94, `_require` generic), `E501` (main.py:371, 105 cols). None compound into anything worse — not re-reported below.
- `uv run mypy src/pyauditor/cli` — clean, `Success: no issues found in 9 source files`.

All files in the package (`main.py`, `bootstrap.py`, `measure.py`, `report.py`, `consolidate.py`, `run.py`, `dependencies.py`, `results.py`) read in full, plus `orchestration/run.py` (consumer of `cli/dependencies.py`) for the Middle Man question.

### Findings

**1. Resilience — non-`OSError` exceptions from core business logic can escape `report`/`consolidate`/`bootstrap` uncaught, unlike `measure`.**

- `src/pyauditor/cli/consolidate.py:101-107` — `build_consolidated_workbook(...)` (line 101) is called with **no** try/except at all; only the subsequent `result.workbook.save(output_path)` is wrapped in `except OSError`. Any `ValueError`/`KeyError`/domain exception raised while building the workbook propagates straight out of `run_consolidate`.
- `src/pyauditor/cli/report.py:117-128` — `build_report(...)` (117-122) only catches `OSError`; `compute_report_glosa(...)` (126-128) is called with no try/except whatsoever.
- `src/pyauditor/cli/bootstrap.py:26-35` — `bootstrap_capa(capa_path)` only catches `OSError`; any other exception type from the Excel-writing path escapes `run_bootstrap`.
- `src/pyauditor/cli/main.py` — `cli_main` (260-411) has no top-level exception handling, so any of the above propagates all the way out of the process as a raw traceback instead of the structured `logger.error` + Result/exit-code-1 pattern the rest of the package establishes.
- By contrast, `src/pyauditor/cli/measure.py:169` **does** wrap its equivalent core call (`measure(...)`, 148-154) in `except Exception`, converting any failure into a structured `IndicatorOutcome` with `hard_failure=True` and continuing the batch — this is the *only* one of the four commands that fully closes this gap. Answer to the ticket's specific question: the `except Exception` in `measure.py` is not the risk — it's justified and correctly scoped (isolates one indicator's failure from aborting the whole batch) — but there's no comment saying so (see finding 8 below), and the real risk is the *absence* of an equivalent broad catch in the other three commands.
- Suggested fix: wrap `build_report`/`compute_report_glosa`/`build_consolidated_workbook`/`bootstrap_capa` calls in `except Exception as exc` (mirroring `measure.py`'s pattern) and convert to the command's own error Result, so no `run_*` function can crash the process with an unhandled traceback.
- Severity: Medium.

**2. Security/data-integrity — `competencia` format validation is not applied uniformly before it becomes a filesystem path segment.**

- Only `src/pyauditor/cli/measure.py:28,93` validates the CLI-supplied `competencia` against `_COMPETENCIA_RE` (`^\d{4}-\d{2}$`) before using it in a path, and even there the check happens *after* `main.py` has already used the raw value to build a log path (see next bullet).
- `src/pyauditor/cli/report.py` and `src/pyauditor/cli/consolidate.py` never validate `competencia`'s format. It flows directly into filesystem paths: `report.py:81` (`roms_dir / competencia`), `report.py:33-44` (`check_report_ready`), `consolidate.py:42` (`report_dir / f"relatorio_{competencia}_{orgao}.xlsx"`), `consolidate.py:45` (`roms_dir / orgao / competencia`).
- `src/pyauditor/cli/main.py:222-227` (`_run_log_path`), `main.py:230-242` (`_extract_report_request`, builds `output_path` from raw `competencia`), and `main.py:245-253` (`_extract_consolidate_request`, same) all build paths from `competencia` before any validation runs — for `measure`, `_run_log_path` (296-298) is even called before `run_measure`'s own regex check executes, so the log file itself is named from unvalidated input.
- Contrast: `measure.py:68-71`'s `_sanitize_indicator_id` *does* sanitize a user/config-influenced string (`config.indicator.id`) before using it as a filename stem — proving the codebase knows how to do this, just doesn't do it consistently for `competencia`.
- Practical impact: a `competencia` value containing `/` or `..` segments (typo, bad script input, no shell involved so no `shell=True`-style RCE, but a single-operator CLI can still mis-target output) creates/reads nested paths silently instead of failing fast with the same "esperado YYYY-MM" message `measure` gives. No test in `tests/test_cli_report.py` / `tests/test_cli_consolidate.py` exercises this (grepped for invalid-competencia cases — none found).
- Suggested fix: hoist `_COMPETENCIA_RE` (or equivalent) into a shared helper (e.g. `cli/results.py` or a new small `cli/validation.py`) and call it once, early, in `main.py` before any request dataclass builds a path — or at minimum replicate `measure.py`'s check at the top of `run_report`/`run_consolidate`, matching the existing per-command validation pattern.
- Severity: Medium.

**3. Clarity/Divergent Change — `main.py`'s `cli_main` still bundles multiple change reasons despite the `_extract_*_request` split.**

- `src/pyauditor/cli/main.py:260-411` — `cli_main` is ~150 lines covering: guided/interactive fallback (264-276), argparse invocation and command narrowing (278-291), and then five inlined dispatch bodies (292-411) that each mix per-orgao fan-out looping, output-path derivation, and (for `report`/`consolidate` only) dependency pre-flight checks.
- This *does* carry Divergent Change risk: the function changes for (a) a new subcommand, (b) fan-out policy changes (`_each_single_orgao`), (c) dependency-check wiring (already inconsistent — see finding 5), and (d) output-path naming conventions. The `_extract_*_request` helpers already solved argv→dataclass parsing; the remaining per-command bodies were not extracted the same way.
- Suggested fix: extract each `elif command == _CMD_X:` body into its own `_dispatch_measure(request) -> int`-style function (mirroring `_extract_measure_request`), so `cli_main` becomes a thin lookup-and-call table and each dispatch path is unit-testable without going through argparse. Not urgent at current size, but the asymmetry in finding 5 is a concrete symptom of the mixing.
- Severity: Low/Medium.

**4. Duplicated code — the `_error` closures in `bootstrap.py`/`measure.py`/`report.py`/`consolidate.py` (ticket's specific question).**

Verdict: **not a real extraction opportunity — leave as-is.** `bootstrap.py` doesn't even have a closure (single exception site, `bootstrap.py:29-35`). The three that do (`measure.py:86-91`, `report.py:67-72`, `consolidate.py:64-69`) each close over a differently-shaped frozen dataclass with different non-error defaults to zero out: `MeasureResult` needs `indicators=()`, `ReportResult` needs `output_path=...` (captured from the outer scope) and `indicator_count=0`, `ConsolidateResult` needs `decisions_preserved=0`. A generic `build_error_result(cls, competencia, orgao, message, **kwargs)` helper would need `**kwargs` for the type-specific fields, which loses exactly the mypy-checked field safety these frozen dataclasses currently get for free (confirmed clean mypy run). The duplicated surface is really just two lines (`logger.error(message)` + a `Result(status="error", ...)` construction) repeated three times — that's load-bearing per-type duplication, not a DRY violation worth introducing an abstraction for. No action recommended.

**5. Operability/consistency — dependency pre-flight checks are applied inconsistently in `main.py`, and bypass the `dependencies.py` registry entirely.**

- `src/pyauditor/cli/main.py:346-356` (`report`) and `main.py:376-384` (`consolidate`) call `check_report_ready`/`check_consolidate_ready` directly before dispatch. `main.py:300-319` (`measure`) and `main.py:320-328` (`bootstrap`) never call `check_measure_ready`/`check_bootstrap_ready`, even though `cli/dependencies.py`'s `CHECKERS` registry lists all four as first-class members.
- Currently harmless — `check_measure_ready` and `check_bootstrap_ready` (`measure.py:51-54`, `bootstrap.py:21-23`) are literal no-ops always returning `satisfied=True` — but `main.py` doesn't use the `CHECKERS` registry at all; it hardcodes direct imports/calls of `check_report_ready`/`check_consolidate_ready`. Only `src/pyauditor/orchestration/run.py:128-138` (`dependency_missing`) actually consumes `CHECKERS`.
- If a future `measure`/`bootstrap` precondition is added, `main.py`'s current pattern requires manually re-adding another inline pre-flight block, whereas routing through `CHECKERS[command]` once (as `orchestration/run.py` already does) would cover all four commands uniformly and keep `main.py` and the orchestrator's dependency-enforcement behavior from drifting apart.
- Severity: Low.

**6. Typing — `cli/dependencies.py`'s `CHECKERS` registry earns its place, but its signature erasure undermines the "no real added logic" question and the skill's typing-strictness principle.**

- `src/pyauditor/cli/dependencies.py:19-24` — not a pure Middle Man: `orchestration/run.py:128-138` (`dependency_missing`) genuinely needs a runtime string→checker lookup (command is a loop variable, not statically known), so the registry has a real second caller/use case.
- However `Callable[..., DependencyCheck]` (dependencies.py:19) erases each checker's actual parameter list. The one real consumer, `orchestration/run.py:128-138`, still has to hardcode `if command == "report": ... elif command == "consolidate": ... else: checker()` to know what arguments to pass — the registry saves an import per command name but doesn't remove the need to know each checker's signature, and mypy cannot catch a wrong-arity call through `Callable[..., ...]`. This is a minor instance of "silenciar o type checker sem justificativa localizada" (the `...` is an implicit blanket suppression of arg-checking, not an explicit one, but has the same effect).
- Suggested fix (optional, low priority): either accept the branching is unavoidable and drop the registry's implied promise of a uniform call (rename/comment to make clear it's a name→function lookup only, not a uniform-call abstraction), or give each checker a `Protocol` so at least `mypy` can flag call-site mismatches — not urgent given the current call sites are already covered by a passing test suite (`tests/test_cli_dependencies.py`).
- Severity: Low.

**7. Tests — missing coverage for the validation gap in finding 2.**

- Grepped `tests/test_cli_report.py` and `tests/test_cli_consolidate.py` for invalid/malformed-`competencia` cases (`../`, regex-format checks) — none found. `measure.py`'s own `_COMPETENCIA_RE` behavior is presumably covered in `tests/test_cli_measure.py` (not independently verified here beyond the grep), but there is no test proving `report`/`consolidate` reject or sanitize a malformed `competencia` the way `measure` does — meaning fixing finding 2 has no regression test to build on yet.
- Severity: Low (paired with finding 2 — fix should ship a test, not standalone).

**8. Clarity — `measure.py:169`'s broad `except Exception` has no comment explaining why it's intentionally wide.**

- `src/pyauditor/cli/measure.py:169-177` — the only broad-`Exception` catch in the package; functionally justified (isolates a single indicator's failure so the rest of the batch still measures — "capturar exceções no nível que possa executar recuperação"), but nothing above the `except Exception` line says so. Given finding 1 shows the other three commands *don't* have an equivalent broad catch, a future reader could "fix" this asymmetry by narrowing `measure.py`'s catch without understanding it's the one command where broad-by-design is correct.
- Suggested fix: one-line comment above `except Exception as exc:` (measure.py:169), e.g. "broad by design — isolates one indicator's failure so the rest of the batch still measures."
- Severity: Low.

### Summary (skill priority order)

1. Resilience: findings 1, 3 (Medium/Low-Medium)
2. Security/data-integrity: finding 2 (Medium)
3. Operability/consistency: findings 5, 6 (Low)
4. Tests: finding 7 (Low)
5. Clarity: findings 4 (no action — verdict only), 8 (Low)

