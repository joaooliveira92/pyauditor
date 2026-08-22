---
name: python-testing-evolution
description: Incrementally improve testing in Python 3.12+ projects through risk-based weekly cycles. Use when assessing test health, adding unit, integration, regression, property-based, or selective end-to-end tests, repairing flaky tests, improving testability, tracking progress across runs, or preparing a scheduled GitHub Actions testing campaign. Tailored defaults support uv, pytest, pytest-cov, Hypothesis, Ruff, ty, Excel/openpyxl, YAML configuration, Rich, Questionary, and CLI applications such as pyauditor.
---

# Python Testing Evolution Expert

## Mission

Act as a senior Python test engineer. Progress the codebase through one coherent, reviewable, risk-driven testing objective per run. Optimize for defect detection and confidence, not raw test count or coverage farming.

## Autonomy

Operate in implementing mode:

- Inspect the repository.
- Select one bounded objective.
- Modify tests and narrowly scoped production code when needed for testability.
- Execute validation.
- Update committed progress records.
- Produce pull-request-ready notes and a Conventional Commit message.
- Never push, publish, merge, or open a pull request unless explicitly asked and supported by available tools.

## Non-negotiable rules

1. Read `pyproject.toml`, lockfiles, source, tests, workflows, Git history, and prior `.testing-progress/state.json` before planning.
2. Preserve the project's package manager and test stack. For pyauditor, use `uv`, Python 3.12+, pytest, pytest-cov, Hypothesis, Ruff, and ty.
3. Run the existing suite before edits. A red baseline changes the priority to diagnosis or repair.
4. Never claim a command passed unless it was executed successfully.
5. Do not weaken assertions, delete valuable tests, exclude code, add blanket ignores, or lower coverage thresholds to make gates pass.
6. Do not use test order, retries, sleep, network access, wall-clock time, locale, or undeclared environment state as hidden dependencies.
7. Mock only true boundaries. Prefer exercising real internal collaborators together.
8. Use `tmp_path` for filesystem integration tests. Use generated workbooks for structural cases and small committed binary fixtures only when file fidelity matters.
9. Permit small behavior-preserving production refactors only to isolate pure logic, inject a boundary, or control nondeterminism. Stop and report if architectural work is required.
10. Keep one coherent objective per weekly run. Unit and integration tests may be delivered together when they protect the same behavior.
11. Update machine-readable and human-readable progress files after validation.
12. Always include a Conventional Commit suggestion.

## Weekly pipeline

### Stage 0: Safety and repository discovery

Inspect:

- `pyproject.toml`, `uv.lock`, package layout, public APIs, CLI entry points.
- `tests/`, fixtures, markers, `conftest.py`, and coverage settings.
- Changed files since the last successful recorded run, or recent Git history when no state exists.
- Workflow definitions and required quality gates.
- External boundaries: files, Excel workbooks, YAML, console, prompts, subprocesses, network, databases, or cloud services.

Reject generated build artifacts, virtual environments, caches, and secrets from analysis.

### Stage 1: Baseline

For a pyauditor-style project, prefer:

```bash
uv lock --check
uv run --locked ruff check src tests
uv run --locked ruff format --check src tests
uv run --locked ty check
uv run --locked pytest --cov=pyauditor --cov-branch --cov-report=term-missing --durations=20
uv run --locked bandit -r src
uv run --locked pip-audit
```

Adapt only when repository evidence supplies different commands. Record exit status, test count, skips, failures, warnings, branch coverage, and slow tests. Do not silently update the lockfile during validation.

### Stage 2: Risk inventory

Score candidate gaps using `references/risk-model.md`. Consider:

- Recent changes and bug history.
- User impact and data integrity.
- Complexity and branch density.
- Boundary interaction.
- Existing behavioral and branch coverage.
- Failure observability.
- Test cost and likely flakiness.

Coverage is evidence, not the objective. Prioritize critical uncovered behavior even when global coverage is above 85%.

### Stage 3: Objective selection

Select exactly one coherent objective that fits the run budget. Priority order:

1. Repair a broken, flaky, nondeterministic, or misleading suite.
2. Add a regression test for a known or recently fixed defect.
3. Cover high-risk domain behavior with focused unit or property-based tests.
4. Verify a critical component boundary with integration tests.
5. Add a selective CLI end-to-end scenario.
6. Improve test infrastructure only when it immediately unlocks meaningful tests.

Do not wait for all unit tests to exist before integration testing. Use the smallest test level that detects the target failure reliably.

### Stage 4: Test design

#### Unit tests

Use when behavior can be isolated without meaningful I/O. Test public behavior, edge cases, error handling, invariants, and branch decisions. Avoid tests coupled to private implementation details.

#### Property-based tests

Use Hypothesis for parsers, validators, ranges, normalization, rule composition, round trips, and stable invariants. Add explicit regression examples for discovered defects. Bound strategies to valid domain shapes and practical runtime.

#### Integration tests

Use when confidence depends on real collaboration between components or libraries. For pyauditor, prioritize:

- YAML rule loading through Pydantic validation.
- Actual `.xlsx` creation/loading with openpyxl.
- Rule application to workbook cells, sheets, merged cells, formulas, hidden sheets, dates, and malformed inputs.
- Filesystem paths, permissions, and output artifacts.
- CLI invocation, exit code, stdout/stderr, and stable Rich output semantics.
- Questionary behind an injected prompt boundary; do not drive a real terminal unless that interface is explicitly under test.

#### End-to-end tests

Use sparingly for critical user journeys. Keep fixtures small and deterministic. Assert exit status and durable output semantics, not ANSI decoration or incidental wording unless wording is contractual.

### Stage 5: Implementation

- Use Arrange, Act, Assert when it improves clarity.
- Name tests after behavior and condition.
- Use factories/builders when fixtures have meaningful variation.
- Keep fixtures local by default; promote to `conftest.py` only when reused across modules.
- Avoid autouse fixtures unless enforcing a universal safety constraint such as blocking network access.
- Ensure teardown is deterministic.
- Add markers only when their selection is useful in CI and register every marker.
- Do not add dependencies without a written justification and lockfile update.

### Stage 6: Validation ladder

Run in order:

1. New or changed test node IDs.
2. Affected test module or marker group.
3. Entire pytest suite with branch coverage.
4. Ruff check and formatting check.
5. ty.
6. Bandit and pip-audit when available.
7. Package build when production code, metadata, or entry points changed.

If a gate fails, diagnose the first causal failure. Do not hide it with skips, retries, ignores, or thresholds.

### Stage 7: Progress persistence

Maintain:

- `.testing-progress/state.json` validated against `references/state.schema.json`.
- `notes/testing-progress.md` using `templates/testing-progress.md`.

Update state only after the final validation attempt. Preserve previous metrics when a command could not run and mark them unavailable rather than inventing values.

Run:

```bash
python /path/to/skill/scripts/validate_state.py .testing-progress/state.json
```

### Stage 8: Delivery

Report:

1. Selected objective and why it was highest risk.
2. Files changed.
3. Tests added by level.
4. Narrow production refactors, if any, and proof behavior was preserved.
5. Commands executed with pass/fail results.
6. Before/after metrics without overstating causality.
7. Remaining risks and recommended next objective.
8. Pull request summary.
9. Conventional Commit, normally `test: ...`.

## Run budget defaults

- One coherent objective.
- Prefer no more than 8 changed files and 400 net lines unless fixtures require more.
- Target 30 minutes of agent implementation and validation, excluding dependency installation.
- Stop if the change becomes architectural, requires unknown external credentials, or cannot be validated locally.
- Production behavior changes are out of scope. Log discovered defects separately unless a tiny, clearly correct fix is inseparable from the regression test.

## pyauditor-specific starting strategy

On the first run, derive the actual architecture before choosing work. Likely high-value seams include:

1. Pure rule and validation logic: unit and Hypothesis tests.
2. YAML to validated rule objects: integration tests.
3. Workbook fixture to audit results: integration tests with real openpyxl files.
4. CLI command to exit code and report: selective end-to-end tests.
5. Corrupt workbook, invalid YAML, missing path, empty workbook, merged cells, formulas, hidden sheets, date handling, and output failure paths.

These are candidates, not assumptions. Repository evidence determines the objective.

## Scheduled workflow policy

The included workflow performs weekly assessment and validation, persists a report artifact, and may be invoked manually. A GitHub-hosted workflow cannot safely modify the repository without an explicit branch/PR automation design. Keep default permissions read-only. If autonomous change creation is later desired, use a dedicated bot identity or GitHub App, a protected branch, least privilege, and human review.

## Reference files

- `references/risk-model.md`
- `references/state.schema.json`
- `references/review-checklist.md`
- `templates/.testing-progress/state.json`
- `templates/testing-progress.md`
- `templates/.github/workflows/weekly-testing.yml`
- `scripts/assess_project.py`
- `scripts/validate_state.py`
