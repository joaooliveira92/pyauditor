# Risk model

Score each candidate from 0 to 3.

- Impact: consequences of failure for correctness, data integrity, or users.
- Change: recent churn or active development.
- Complexity: branches, parsing, transformations, and state transitions.
- Boundary: filesystem, workbook format, CLI, configuration, or external system interaction.
- Coverage gap: missing behavioral or branch protection.
- Defect evidence: known bug, flaky behavior, warning, or production incident.
- Observability deficit: failure is hard to detect or diagnose.
- Test feasibility: 3 means a deterministic test is inexpensive; 0 means blocked or architectural.

Priority score:

`impact * 3 + defect_evidence * 3 + change * 2 + boundary * 2 + complexity + coverage_gap + observability_deficit + test_feasibility`

Use judgment. The score ranks candidates but never overrides a red baseline, security concern, or known data-corruption risk.
