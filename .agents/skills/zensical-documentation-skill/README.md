# Zensical Documentation Skill

A reusable AI skill for planning, authoring, scaffolding, and validating technical documentation, product manuals, and developer portals in Markdown with Zensical.

## Install

Copy the `zensical-documentation-skill` directory into the skills directory used by your agent platform. Keep `SKILL.md`, `references`, `assets`, and `scripts` together.

## Smoke test

```bash
python scripts/scaffold.py /tmp/example-docs --site-name "Example Docs"
python scripts/validate_docs.py /tmp/example-docs
```

If Zensical is installed:

```bash
cd /tmp/example-docs
zensical build --strict
```
