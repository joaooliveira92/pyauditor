---
name: zensical-documentation
version: 1.0.0
description: Design, write, scaffold, validate, and maintain feature-rich technical documentation, product manuals, API guides, and developer portals in Markdown, using Zensical as the default static-site generator.
license: MIT
metadata:
  author: João Antonio Carvalho Monteiro de Oliveira
  tags: [documentation, markdown, zensical, developer-portal, product-manual, technical-writing]
---

# Zensical Documentation Builder

## Purpose

Use this skill when the user asks to create or improve:

- technical documentation sites;
- product manuals and operational handbooks;
- developer portals;
- getting-started guides, tutorials, how-to guides, explanations, and references;
- API, CLI, SDK, configuration, architecture, deployment, troubleshooting, or release documentation;
- an information architecture, navigation model, content plan, Markdown documentation set, or Zensical project.

Zensical is the default publishing engine. Write source content in Markdown and use `zensical.toml` for new projects. Preserve an existing `mkdocs.yml` when migration or compatibility is explicitly required.

## Non-goals

Do not invent product behavior, API contracts, commands, screenshots, compatibility claims, or configuration keys. Mark missing facts with explicit TODOs and list them in the delivery report. Do not overwrite user files without creating a backup or writing output to a new location.

## Required workflow

### 1. Inspect the source of truth

Collect and classify available inputs: repository files, requirements, code, OpenAPI/AsyncAPI specifications, CLI help, existing docs, ADRs, tickets, release notes, and brand guidance. Prefer product artifacts over assumptions.

If a repository is available, inspect at minimum:

- root manifests and workspace configuration;
- public packages/modules;
- API schemas and generated types;
- executable entry points and CLI commands;
- examples and tests that expose real usage;
- deployment and environment configuration;
- existing documentation and contribution rules.

Record contradictions and unknowns. Never silently resolve uncertain product facts.

### 2. Identify audience and documentation mode

Infer when evidence is strong; otherwise state assumptions. Define:

- primary and secondary audiences;
- user goals and prerequisite knowledge;
- supported platforms and versions;
- documentation type: tutorial, how-to, explanation, or reference;
- expected maintenance owner and release cadence.

Use `references/content-model.md` to structure the information architecture.

### 3. Produce a documentation plan

Before bulk authoring, create a concise plan containing:

- audience and jobs-to-be-done;
- proposed navigation tree;
- page inventory with purpose and owner;
- source-to-page traceability;
- terminology decisions;
- unknowns/TODOs;
- acceptance criteria.

For small requests, keep this plan in the delivery report. For full portals, create `docs/about/documentation-plan.md` unless it would expose internal-only information.

### 4. Scaffold or preserve the Zensical project

For a new project, prefer the official CLI:

```bash
zensical new <project-directory>
```

If execution is unavailable, use:

```bash
python scripts/scaffold.py <project-directory> --site-name "Product Documentation"
```

For an existing project:

- preserve its conventions;
- update navigation deliberately;
- avoid deleting extensions, theme settings, custom CSS, JavaScript, or build automation;
- use relative links to Markdown source files;
- avoid both `README.md` and `index.md` in the same documentation directory.

### 5. Author content

Apply the rules in `references/style-guide.md` and page templates in `assets/templates/`.

Every task-oriented page should include, when applicable:

1. a clear outcome-focused title;
2. a one-paragraph summary;
3. prerequisites;
4. numbered steps with copyable examples;
5. expected result or verification;
6. troubleshooting or failure modes;
7. next steps and related pages.

Every reference page should be exhaustive but scannable. Use stable headings, consistent parameter descriptions, defaults, constraints, examples, error behavior, and version notes.

For developer portals, include only evidence-backed sections from this baseline:

- overview and quickstart;
- concepts and architecture;
- authentication and authorization;
- API/SDK/CLI reference;
- integration guides and examples;
- environments, limits, errors, observability, and webhooks/events;
- deployment and operations;
- troubleshooting;
- changelog, support, and contribution guidance.

For product manuals, consider:

- safety and support boundaries;
- installation and setup;
- feature workflows;
- roles and permissions;
- administration;
- backup, recovery, and maintenance;
- troubleshooting and diagnostics;
- glossary and specifications.

### 6. Configure Zensical

Use `zensical.toml` for new projects. Keep configuration conservative and confirm version-specific options against the installed CLI or official documentation. Start with:

```toml
[project]
site_name = "Product Documentation"
site_description = "Technical documentation and user guides"
site_author = "Documentation Team"

[project.theme]
variant = "modern"
```

Only add navigation, extensions, plugins, analytics, social cards, search tuning, custom assets, or repository links when the syntax is verified for the installed Zensical version.

### 7. Validate

Run the local validator:

```bash
python scripts/validate_docs.py <project-directory>
```

When Zensical is installed, run a strict production build:

```bash
zensical build --strict
```

Also preview the site using the preview command reported by `zensical --help`. Inspect the rendered site at desktop and mobile widths. Check navigation, search, code blocks, tables, admonitions, anchors, focus order, contrast, and overflow.

Do not claim a successful Zensical build unless it was actually executed and returned success.

### 8. Deliver

Return:

- created and modified file paths;
- a short navigation/content summary;
- validation commands executed and their results;
- unresolved TODOs or unverified claims;
- compatibility or migration notes;
- a recommended Conventional Commit message.

Suggested commit:

```text
docs: add Zensical documentation portal
```

## Quality gates

A delivery is complete only when all applicable gates pass:

- **Accuracy:** factual claims map to a source or are explicitly marked as assumptions/TODOs.
- **Task success:** setup and quickstart steps are executable and include a verification outcome.
- **Findability:** navigation labels use user language and important content is reachable without deep nesting.
- **Consistency:** terminology, capitalization, filenames, headings, and code style are uniform.
- **Link integrity:** relative Markdown links and local assets resolve.
- **Accessibility:** meaningful link text, alt text, heading hierarchy, keyboard-readable structure, and no color-only meaning.
- **Security:** no secrets, real tokens, unsafe defaults, or production credentials appear in examples.
- **Maintainability:** ownership, version scope, reusable snippets, and update triggers are clear.
- **Build:** local validation passes; strict Zensical build passes when Zensical is available.

## Progressive enhancement

Prefer portable Markdown first. Add Zensical-supported enhancements only when they improve comprehension, such as admonitions, tabs, annotations, diagrams, code highlighting, footnotes, or content metadata. Provide a readable fallback and avoid decorative complexity.

## Reference files

- `references/content-model.md`: information architecture and page taxonomy.
- `references/style-guide.md`: editorial, Markdown, accessibility, and code-example rules.
- `references/validation-checklist.md`: human and automated review checklist.
- `assets/templates/`: reusable Markdown page templates.
- `scripts/scaffold.py`: dependency-free starter project generator.
- `scripts/validate_docs.py`: dependency-free Markdown/link/frontmatter validator.
