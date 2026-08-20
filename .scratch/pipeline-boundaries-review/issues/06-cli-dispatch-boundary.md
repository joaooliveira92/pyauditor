Type: research
Status: resolved

## Question

`cli/main.py` faz o dispatch para `bootstrap.py`/`measure.py`/`report.py`/`results.py`/`consolidate.py`/`run.py`, incluindo checagens de dependência pré-flight (`dependencies.py`, registro `CHECKERS`). Rastreie a fronteira entre `main.py` e cada subcomando: quais argumentos/flags cada subcomando espera vs. o que `main.py` efetivamente valida antes de despachar (ex.: `competencia`, já sabemos por `production-readiness-review` ticket 05 que só `measure.py` valida o formato — aqui o objetivo é mapear todo o dispatch, não só esse campo); onde uma exceção de um subcomando escaparia sem handler no nível de `cli_main`; e se o registro `CHECKERS` cobre de fato todos os subcomandos que fazem I/O externo. Não repita achados de qualidade interna já cobertos em `.scratch/production-readiness-review/issues/05-cli-package-review.md` — foque só na travessia main→subcomando.

Aplique o skill `python-production-engineer` (ler `.agents/skills/python-production-engineer/SKILL.md` por inteiro) para julgar severidade. Achados citam `file:line`.

## Answer

All 8 files in `src/pyauditor/cli/` read in full, plus `src/pyauditor/orchestration/run.py` (consumer of `cli/dependencies.py`, and the `run` subcommand's own internal dispatch loop), `src/pyauditor/logging.py` (`setup_logging`), `src/pyauditor/config/manifest.py` (`load_manifest`), and `src/pyauditor/atomic_write.py`/`src/pyauditor/excel/glosas.py` (atomic-write call sites). Note: since `.scratch/production-readiness-review/issues/05-cli-package-review.md` was written, several of its findings were already fixed (`bootstrap.py`/`report.py`/`consolidate.py` now all wrap their core calls in `except Exception`, and `cli_main` is now split into `_dispatch_*` functions) — this review starts from the current code, not from ticket 05's snapshot, and focuses only on the `main.py` ↔ subcommand crossing itself, not internal command-body quality.

### Findings (skill priority order)

**1. Corretude — the `--manifest` CLI flag is parsed and validated but silently discarded before dispatch; it never affects what `measure` actually runs.**

- `src/pyauditor/cli/main.py:192-206` (`_extract_measure_request`) computes `MeasureRequest.manifest_path` honoring the user's `--manifest` override when given (falls back to `config_dir/orgao/datasets.yaml` only when `--manifest` is absent, main.py:192-197).
- `src/pyauditor/cli/main.py:273` (`_dispatch_measure`) never reads `request.manifest_path` — it recomputes `per_orgao_manifest_path = request.config_dir / orgao / "datasets.yaml"` from scratch, unconditionally, then loads that (main.py:276-277). Confirmed via grep: `request.manifest_path`/`MeasureRequest.manifest_path` has exactly one write site (main.py:203) and zero read sites anywhere in the package.
- Impact: a user running `pyauditor measure 2026-06 --manifest custom.yaml` gets no error, no warning — the flag is accepted by argparse, stored on the validated request dataclass, and then thrown away at the exact main.py→subcommand crossing. `measure` silently falls back to the default manifest instead. This is precisely the "what main.py validates vs. what dispatch actually uses" mismatch this ticket asked to map, and it's the most severe instance found: not a missing validation, but a validated value never reaching its consumer.
- Suggested fix: `_dispatch_measure` should derive `per_orgao_manifest_path` from `request.manifest_path` (adjusted per órgão only when the user didn't override it), not recompute independently of it.
- Severity: High.

**2. Resiliência — `setup_logging`'s filesystem I/O is unguarded in every one of the 5 `_dispatch_*` functions, and `cli_main` has no top-level exception handler at all.**

- `src/pyauditor/logging.py:43` (`setup_logging`) does `path.parent.mkdir(parents=True, exist_ok=True)` before adding the file sink — this raises `OSError` on a read-only filesystem, permission-denied directory, or a path with invalid components.
- Every dispatch function calls `setup_logging(log_path=_run_log_path(...))` completely unguarded: `main.py:262-267` (`_dispatch_measure`), `main.py:296` (`_dispatch_bootstrap`), `main.py:303-307` (`_dispatch_report`), `main.py:343-347` (`_dispatch_consolidate`), `main.py:373-375` (`_dispatch_run`).
- `cli_main` itself (`main.py:388-431`) has no try/except anywhere in its body.
- Net effect: any of the above `setup_logging` calls raising `OSError` produces a raw, unstructured traceback straight out of the process — before any of the well-structured per-command `Result`/exit-code error handling ever runs (that machinery only guards the run_* business logic *after* logging is already set up). This confirms and extends the "uncaught exception escapes past cli_main" concern from ticket 05: it's not just internal command bodies, it's the dispatch layer's own first I/O act, present identically across all 5 subcommands.
- Suggested fix: wrap each `setup_logging(...)` call (or better, factor a single `_setup_logging_for(command, ...)` helper used by all five dispatch functions) in `try/except OSError`, logging to stderr and returning exit code 1 on failure, mirroring the pattern every `run_*` function already uses for its own I/O.
- Severity: Medium.

**3. Segurança/data-integrity — `_run_log_path` embeds unvalidated `competencia` into a path segment, and `Path.__truediv__` turns an embedded `/` into real subdirectories.**

- `src/pyauditor/cli/main.py:222-227` (`_run_log_path`) builds `log_dir / f"pyauditor-{command}{suffix}-{stamp}.log"` where `suffix = f"-{competencia}"` and `competencia` is the raw CLI argument — no validation has run yet at this point (validation only happens later, inside `run_measure`/`run_report`/`run_consolidate` via `validate_competencia`, `src/pyauditor/cli/results.py:17-24`).
- This is called before dispatch for every competencia-taking subcommand: `main.py:262-267` (measure), `main.py:303-307` (report), `main.py:343-347` (consolidate), `main.py:373-375` (run). `bootstrap` is unaffected (no `competencia` argument).
- Mechanic beyond what ticket 05 already flagged (which characterized this as "misdirected output"): because the resulting string is joined with `Path.__truediv__` (`log_dir / f"...{suffix}..."`), a `competencia` value containing `/` (e.g. `../../tmp/x`) is not just an odd filename — it produces genuine nested path segments, and `setup_logging` (`src/pyauditor/logging.py:43`) then calls `mkdir(parents=True, exist_ok=True)` on that joined path, i.e. it will silently create directories at an attacker/typo-controlled location relative to `log_dir`, before any competencia-format error is ever raised.
- Combined with finding 6 below (no output-directory containment anywhere in the package — `--output-dir`/`--report-dir`/`--capa-path`/`--data-dir` accept arbitrary paths, including absolute ones, with no check they stay under the project root), a malformed `competencia` can cause writes outside the intended tree with no error until much later, if at all.
- Suggested fix: call `validate_competencia` (or hoist the same `_COMPETENCIA_RE`) once in `cli_main`/each `_extract_*_request`, before `_run_log_path` is ever invoked, not just inside the deeper `run_*` functions.
- Severity: Medium.

**4. Resiliência/corretude — `execute_run`'s dispatch loop has no exception boundary, so a crash there leaves the run's persisted state permanently stuck at `"running"`, bypassing the whole retry/skip/abort contract.**

- `src/pyauditor/orchestration/run.py:279-286` — the state is persisted as `status="running"` (279-284, `save_state(path, state)`) immediately before `result = _dispatch(command, orgao, request)` (286) is called with **no** try/except around it.
- `_dispatch`'s `measure` branch (`orchestration/run.py:159-171`) calls `load_manifest(manifest_path)` (162) unguarded — mirrors the identical unguarded call in `main.py:277`. `load_manifest` (`src/pyauditor/config/manifest.py:97-105`) documents that it raises `ValueError` for malformed YAML and `FileNotFoundError` — neither is a `Result`, so it can't flow through `record_failure_and_decide` (`orchestration/run.py:224-248`), the single seam this state machine uses for every other failure mode.
- Consequence: the exception propagates out of `execute_run` → `run_run` (`cli/run.py:42`) → `_dispatch_run` (`main.py:376`) → `cli_main`, uncaught (see finding 2), crashing the process — but by then the state file on disk already has that step at `status="running"` (saved at line 283, before the crash). The `on_failure`/`on_state_change` callbacks the interactive layer (`interactive/flow.py`, per the module docstring) depends on for showing a graceful failure prompt never fire for this failure mode. The presence of `reset_stale_running` (imported and applied in `_ensure_state`, `orchestration/run.py:127`) shows the orchestrator already anticipates "stale running" states from crashes — but `load_manifest` is a concrete, reachable way to trigger exactly that scenario without going through the state machine's designed recovery path (it only fixes the state on the *next* run, and doesn't record a proper `error` entry with `error_message` on the crashed run itself).
- Suggested fix: wrap `_dispatch(command, orgao, request)` in `execute_run`'s loop in a `try/except Exception`, converting any escape into the same `record_failure_and_decide` path already used for `Result.status == "error"`, so a load-time exception behaves identically to a business-logic failure from the state machine's point of view.
- Severity: Medium-High (state corruption + bypasses the failure-handling contract this module exists to provide).

**5. Resiliência — the two production call sites around `atomic_write` only catch `OSError`, but `atomic_write`'s own contract is exception-type-agnostic.**

- `src/pyauditor/atomic_write.py:16-29` — `atomic_write(path, write)`'s docstring says "On any exception, the temp file is removed" and the implementation catches `BaseException` (line 27) to clean up, then re-raises the *original* exception unchanged — i.e. it's explicitly designed so callers must be ready to catch whatever `write()` can raise, not just `OSError`.
- `src/pyauditor/cli/consolidate.py:120-122` wraps `atomic_write(output_path, result.workbook.save)` in `except OSError` only. `result.workbook.save` is `openpyxl`'s `Workbook.save`, which can raise `openpyxl`-internal exceptions unrelated to `OSError` on a malformed workbook object.
- `src/pyauditor/cli/report.py:145-147` wraps `write_historico(historico_path, historico)` in `except OSError` only; `write_historico` (`src/pyauditor/excel/glosas.py:124-126`) calls `json.dumps(historico, ...)` *before* even entering `atomic_write` — a non-serializable value in `historico` (built from `historico_entry`, `glosas.py:129-136`, currently only primitives, but not type-enforced at that boundary) would raise `TypeError` outside `atomic_write`'s own exception handling entirely, propagating straight past this `except OSError`.
- Both are asymmetric with the rest of these same functions: `consolidate.py:112-117` and `report.py:127-136` already use `except Exception` for the equivalent core-logic calls (per the fix already applied since ticket 05) — only the final persistence step regressed to the narrower catch.
- Suggested fix: broaden both to `except Exception`, consistent with the rest of `run_consolidate`/`run_report` and with `atomic_write`'s documented contract.
- Severity: Low-Medium.

**6. Operabilidade — `CHECKERS` covers every subcommand with filesystem side effects reachable from `cli_main`, but no checker (registered or ad-hoc) validates *writability* — only *pre-existence* of upstream artifacts.**

- No network I/O exists anywhere in the codebase (grepped for `requests`/`httpx`/`urllib`/`socket` — no matches outside test tooling); every external boundary in this package is the local filesystem.
- `src/pyauditor/cli/dependencies.py:19-24` (`CHECKERS`) registers `bootstrap`/`measure`/`report`/`consolidate` — the four Commands `cli_main` can dispatch directly with filesystem effects. `run` has no entry, but that's by design: it's a meta-command whose four constituent phases are checked per-step through `dependency_missing` (`orchestration/run.py:135-152`), a separate, already-reviewed (ticket 05 finding 6) precondition path.
- All four `check_*_ready` functions (`bootstrap.py:21-23`, `measure.py:50-53`, `report.py:32-44`, `consolidate.py:38-48`) only test read-side preconditions — does an expected input file/dir already exist. None of them, nor anything else in the dispatch path, checks that the *output* location (`log_dir` for `setup_logging`, `output_dir`/`report_dir`/`capa_path`'s parent) is writable before the command starts doing real work. This is the concrete gap behind finding 2: the first filesystem write of every subcommand (the log file) has zero pre-flight coverage, registered or otherwise.
- Severity: Low.

### Summary (skill priority order)

1. Corretude: finding 1 (High)
2. Segurança/data-integrity: finding 3 (Medium)
3. Resiliência: findings 4 (Medium-High), 2 (Medium), 5 (Low-Medium)
4. Operabilidade: finding 6 (Low)
