# Python Testing Evolution skill

A risk-driven, incremental testing skill for Python 3.12+ projects. It selects one coherent weekly objective, implements unit and integration coverage where appropriate, validates the complete project, and persists progress across runs.

## Install

Copy this directory to the agent's skills directory. Copy files under `templates/` into the target repository as needed. For the supplied GitHub Actions workflow, also copy `scripts/assess_project.py` to the repository's `scripts/` directory.

## Production note

The workflow uses readable action release tags. Replace each third-party action reference with an audited full commit SHA before production use.
