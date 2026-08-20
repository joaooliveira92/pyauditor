Type: research
Status: resolved

## Question

`orchestration` (`run.py`, `state.py`, `summary.py`) recebe `RunRequest` construído por `cli/*.py` e por `interactive/flow.py`, escreve resultados para `rom`, e persiste `state.py` entre execuções (retomada/resume). Rastreie três fronteiras: (1) `cli`/`interactive` → `orchestration`: os dois caminhos de construção de `RunRequest` produzem exatamente o mesmo shape/invariantes, ou há campo que só um dos dois valida? (2) `orchestration` → `rom`: o que `orchestration` escreve e o que `rom` espera ler de volta (ver também ticket 04, não duplique achados de leitura). (3) `state.py` persistido → lido de volta numa run futura: o que muda entre a versão escrita e o que o código atual espera ler (schema drift entre execuções separadas no tempo). Não repita achados de qualidade interna já cobertos em `.scratch/production-readiness-review/issues/05-cli-package-review.md` e `06-orchestration-package-review.md` — foque só na travessia.

Aplique o skill `python-production-engineer` (ler `.agents/skills/python-production-engineer/SKILL.md` por inteiro) para julgar severidade. Achados citam `file:line`.

## Answer

Files read in full: `src/pyauditor/orchestration/run.py`, `state.py`, `summary.py`; `src/pyauditor/cli/main.py`, `bootstrap.py`, `measure.py`, `report.py`, `consolidate.py`, `run.py`, `dependencies.py`, `results.py`; `src/pyauditor/interactive/flow.py`, `provider.py`. Cross-checked against `.scratch/production-readiness-review/issues/05-cli-package-review.md` and `06-orchestration-package-review.md` to avoid repeating internal-quality findings — both are already resolved and their fixes (`validate_competencia` shared helper, `RunStateCorrupted`, `_ARTIFACT_FORMATTER_FOR_TYPE` dict) are visible in the current code, confirmed below where relevant.

### Sub-boundary 1 — `cli`/`interactive` → `orchestration` (`RunRequest` construction parity)

**Finding A — `src/pyauditor/cli/main.py:214-219` vs `src/pyauditor/orchestration/run.py:77-80` — Major (corretude/perda de dados) — two independently-maintained `_capa_path_for` helpers compute a different physical path for the same `(capa_path, orgao)` input whenever `capa_path` is customized to a non-default directory.**

- `cli/main.py:214-219`:
  ```python
  def _capa_path_for(capa_path: Path, orgao: Orgao) -> Path:
      if capa_path != _DEFAULT_CAPA_PATH:
          return capa_path
      if orgao == "both":
          return _DEFAULT_CAPA_PATH
      return Path(f"capa_{orgao}.xlsx")
  ```
  compares the **whole path** against the default (`_DEFAULT_CAPA_PATH = Path("capa.xlsx")`, `main.py:44`).
- `orchestration/run.py:77-80`:
  ```python
  def _capa_path_for(capa_path: Path, orgao: str) -> Path:
      if capa_path.name != _DEFAULT_CAPA_NAME or orgao == "both":
          return capa_path
      return capa_path.parent / f"capa_{orgao}.xlsx"
  ```
  compares only the **filename** against the default (`_DEFAULT_CAPA_NAME = "capa.xlsx"`, `run.py:41`).
- Verified empirically: for `capa_path=Path("artifacts/capa.xlsx")`, `orgao="MinC"` → `cli/main.py`'s version returns `artifacts/capa.xlsx` unchanged (it only "is default" when the *entire* path equals `Path("capa.xlsx")`, so a custom directory always counts as "user override" and skips per-órgão suffixing). `orchestration/run.py`'s version returns `artifacts/capa_MinC.xlsx` (it only compares the filename, so a custom directory still gets the per-órgão suffix applied). Same for `orgao="MTur"` → cli returns the identical `artifacts/capa.xlsx` again.
- Impact, two distinct failure modes:
  1. **Collision inside a single cli invocation**: `pyauditor bootstrap --orgao both --capa-path artifacts/capa.xlsx` fans out per órgão via `_each_single_orgao` (`main.py:256-257`, called from `_dispatch_bootstrap`/`_dispatch_measure`/`_dispatch_report`, `main.py:290-338`) but both órgãos resolve to the *same* `artifacts/capa.xlsx` — MTur's bootstrap overwrites MinC's capa file (or vice versa, order-dependent), and `measure`/`report` for one órgão silently read the other órgão's capa fields (fiscal names, identification) into its ROM.
  2. **Cross-entry-point mismatch**: a workflow that mixes standalone `cli/main.py` subcommands (e.g. `pyauditor bootstrap --capa-path artifacts/capa.xlsx --orgao MinC`) with the orchestrated `pyauditor run` or the interactive guided flow (both routed through `orchestration/run.py`'s `_dispatch`, `run.py:155-189`) writes/reads two different physical files for what the user believes is one input — `bootstrap` (via cli) writes `artifacts/capa.xlsx`, but a later `pyauditor run` resuming `report` for the same órgão (via orchestration) looks for `artifacts/capa_MinC.xlsx`, finds nothing, and fails `dependency_missing` (`run.py:135-152`) even though the capa genuinely exists at the other path.
  3. This affects every phase that touches capa: `_dispatch_bootstrap`/`_dispatch_measure`/`_dispatch_report` in `main.py` (lines 295, 274, 310) all call the cli version; `_dispatch`'s `bootstrap`/`measure`/`report` branches in `orchestration/run.py` (lines 157, 170, 176) all call the orchestration version.
  - No test exercises a non-default capa directory with `orgao="both"` or cross-checks the two `_capa_path_for` implementations against each other — grepped `tests/` for `capa_MinC.xlsx`/`capa_MTur.xlsx`, only default-directory cases are covered (`tests/test_cli_main.py:75,114`, `tests/test_measure.py:82,100,119`).
  - Suggested fix: delete one of the two duplicate functions and share the other (move to `cli/results.py` or a small shared module both `cli` and `orchestration` import), so there is exactly one definition of "what counts as the default capa path" for the whole pipeline.

**Finding B — `src/pyauditor/interactive/flow.py:47-52,78-85` vs `src/pyauditor/cli/main.py:368-386` (`_dispatch_run`) — Medium (resiliência/operabilidade) — `competencia` format is validated on the interactive path before `RunRequest` is built, but not on the `cli run` path.**

- `interactive/flow.py:47-52` (`_validate_competencia`, using `_COMPETENCIA_RE` at `flow.py:22`) is wired as the `validate=` callback for `provider.ask_text` in `collect_answers` (`flow.py:78-85`) — a malformed competência is rejected and re-prompted *before* `GuidedAnswers`/`RunRequest` is ever constructed (`flow.py:102-107`).
- `cli/main.py:368-386` (`_dispatch_run`) takes `competencia` straight from the argparse positional (`main.py:173`, no `type=`/format check, unlike `--orgao`'s `choices=` at `_add_orgao_argument`, `main.py:105-112`) and passes it straight into `run_run` → `RunRequest` (`cli/run.py:19-40`) → `execute_run` with **no** format check anywhere in that path.
- Consequence: `execute_run`'s phase-major plan (`orchestration/run.py:83-91`) runs `bootstrap` *first*, and `run_bootstrap` (`cli/bootstrap.py`) never looks at `competencia` at all — so a `pyauditor run not-a-date --orgao MinC` invocation successfully creates/overwrites a real capa file before the `measure` phase's own `validate_competencia` check (`cli/measure.py:92-94`, confirmed the shared helper from the closed cli review is in place and runs first thing inside `run_measure`) finally reports the error. Individual subcommands (`pyauditor measure not-a-date`) don't have this problem because `run_measure`/`run_report`/`run_consolidate` all validate before touching any output (`measure.py:92-94`, `report.py:77-79`, `consolidate.py:75-77`) and bootstrap is never in their call path.
- Not data corruption (no downstream command ever misinterprets the bad string as a real path segment — `validate_competencia` catches it before any `year, month = competencia.split("-")`), but it is a real asymmetry between the two `RunRequest`-construction paths this ticket asked about: same field, validated pre-construction on one path, only validated several phases deep (after a real side effect) on the other.
- Suggested fix: call `validate_competencia` (already shared in `cli/results.py`) at the top of `_dispatch_run`, mirroring what `interactive/flow.py` does at prompt time, and fail fast with the same message before `execute_run`/`bootstrap` ever runs.

**Other `RunRequest` fields checked, no drift found:** `orgao` is constrained identically on both paths (argparse `choices=("MinC","MTur","both")` for cli, `ask_choice` with a fixed 3-option list for interactive) — both are closed-set selections, not free text, so no validation gap. `config_dir`/`data_dir`/`output_dir`/`report_dir`/`capa_path` are unvalidated free-text `Path`s on *both* paths symmetrically (neither existence-checks them before `RunRequest` construction) — not a boundary asymmetry, just a shared (and out-of-scope, already-known) gap. `commands`: `cli run` has no `--commands` flag and always passes the `RunRequest` default `_ALL_COMMANDS` (`orchestration/run.py:56`); interactive's `select_commands` (`flow.py:111-127`) can produce any subset including the empty set. This is a feature-surface difference, not a validation gap — an empty/partial selection is handled safely by `execute_run`'s `command not in request.commands` skip branch (`run.py:250-257`) regardless of which path produced it.

### Sub-boundary 2 — `orchestration` → `rom` (kept light per ticket; ticket 04 owns the `rom`→excel read side)

- `orchestration` adds no new write/read contract of its own — `_dispatch` (`run.py:155-189`) calls exactly the same `run_bootstrap`/`run_measure`/`run_report`/`run_consolidate` functions the standalone cli subcommands call, with the same argument shapes (confirmed manifest-path construction, `.json` sidecar output paths, and `relatorio_*` naming are byte-identical between `cli/main.py`'s per-command dispatch functions and `orchestration/run.py`'s `_dispatch`, except for the capa-path divergence in Finding A above, which affects this boundary too since `bootstrap` is the write side and `report`/`measure` are the read side of the capa contract).
- The `measure` → `.json` sidecar → `report` round-trip (`cli/measure.py:145-157` writes via `summarize(result).to_dict()`; `cli/report.py:47-52` reads via `IndicatorSummary(**raw)`) is guarded by `IndicatorSummary.__post_init__` (`rom/summary.py:41-52`), which raises `TypeError` on any type mismatch at load time rather than deep in Excel-building arithmetic — this is unchanged by going through `orchestration` vs. standalone cli, so no additional finding here; full treatment left to ticket 04.

### Sub-boundary 3 — `state.py` persisted → reloaded in a future run (schema drift)

**Already resolved by the fix from `06-orchestration-package-review.md` finding 1 — confirmed in current code, no new defect found.**

- `state.py:62-75` (`load_state`) wraps `json.loads` + `CommandStateEntry(**entry)` construction in `try/except (json.JSONDecodeError, KeyError, TypeError)`, raising the actionable `RunStateCorrupted(path, reason)` (`state.py:28-38`) instead of a raw traceback. `_ensure_state` (`orchestration/run.py:115-132`) catches `RunStateCorrupted` and logs+starts the run from scratch (`run.py:118-121`) rather than crashing `execute_run`.
- Verified this covers every schema-drift shape a future code version could produce against an older persisted file: a **new required field** added to `CommandStateEntry` → missing key → `TypeError` on construction → caught. A **renamed field** → old key becomes an unexpected kwarg → `TypeError` → caught. A **new field with a default** → old file simply omits it, dataclass default fills in → loads cleanly (true forward-compatibility, not just crash-avoidance). An **unknown/retyped `status` value** → explicitly checked against `_VALID_STATES` post-construction (`state.py:70-72`) → `RunStateCorrupted`, not a `KeyError` deep in `summary.py`'s `_STATE_ICON[entry.status]` lookup (`summary.py:24-30,119`) — this closes the specific compounding risk review 06's finding 8 flagged.
- Residual, non-blocking observation (Minor, informational only — not a new defect): schema drift is handled by **total discard** of the old state (fresh `pending` plan, `run.py:122-126`), never partial migration. That is the documented, deliberate design (`state.py:1-12`, `RunStateCorrupted` docstring `state.py:28-33`: "the filesystem, not this file, is the source of truth"), and it's the right call given `state.py`'s own stated role as a resume *cache*, not a system of record — flagging only so this ticket's sub-boundary-3 question has an explicit answer: drift is tolerated (no crash), not migrated (no attempt to preserve any still-valid entries from a partially-recognizable old file).

### Summary (skill priority order)

1. Corretude/perda de dados: Finding A (Major) — divergent `_capa_path_for` implementations across the cli↔orchestration boundary can silently collide or mismatch capa files.
2. Resiliência/operabilidade: Finding B (Medium) — `cli run`'s `competencia` isn't validated before `bootstrap` runs, unlike the interactive path.
3. Sub-boundary 2 (orchestration→rom): no new finding, contract is identical to the already-reviewed cli↔rom contract.
4. Sub-boundary 3 (state.py schema drift): no new finding — already fixed by the closed orchestration review; confirmed robust against every drift shape checked, with one informational note about total-discard-not-migration being the deliberate, correctly-documented design.
