# Content model

## Use a task-centered taxonomy

Classify each page by its primary job:

- **Tutorial:** guided learning experience for a beginner, with a controlled path and visible result.
- **How-to:** goal-oriented procedure for a user who already understands the basics.
- **Explanation:** conceptual context, tradeoffs, architecture, and rationale.
- **Reference:** precise, complete facts meant to be consulted rather than read linearly.

Do not mix all four modes on one long page. Link between them.

## Recommended portal architecture

```text
docs/
  index.md
  getting-started/
    index.md
    installation.md
    quickstart.md
  guides/
    index.md
  concepts/
    index.md
    architecture.md
  reference/
    index.md
    configuration.md
    cli.md
    api.md
  operations/
    index.md
    deployment.md
    observability.md
    troubleshooting.md
  release-notes/
    index.md
  contributing.md
  glossary.md
```

Adapt this structure to user goals. Avoid empty sections and navigation deeper than necessary.

## Page inventory fields

For each planned page record: title, path, type, audience, user goal, prerequisites, source of truth, owner, version scope, status, and related pages.

## Naming

Use lowercase kebab-case filenames. Use nouns for concepts and verbs or outcomes for procedures. Keep navigation labels short, distinct, and understandable without internal product vocabulary.
