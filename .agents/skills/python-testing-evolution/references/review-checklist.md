# Test review checklist

- The test fails for the intended defect or missing behavior before the fix when demonstrable.
- Assertions validate observable behavior, not merely execution.
- Happy path, meaningful edge case, and failure behavior are considered.
- Test data is minimal, explicit, and domain-representative.
- No network, wall clock, locale, order, random seed, or machine-specific dependency leaks in.
- Mocking occurs only at a true boundary.
- Temporary files and resources are cleaned deterministically.
- Integration tests use real serialization when fidelity matters.
- Hypothesis strategies represent the domain and have bounded runtime.
- Coverage changes are interpreted alongside risk and branch behavior.
- Validation commands and outcomes are recorded honestly.
