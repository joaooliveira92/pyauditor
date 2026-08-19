# Validation checklist

## Automated

- The configuration file exists.
- The docs directory and home page exist.
- Markdown files contain exactly one H1 unless the project intentionally derives titles elsewhere.
- Local links and image paths resolve.
- Heading fragments resolve.
- No `README.md` and `index.md` conflict exists in one directory.
- No obvious secret patterns or unresolved placeholders remain.
- `zensical build --strict` succeeds when Zensical is installed.

## Human review

- A new user can identify the product and complete the quickstart.
- Each procedure has prerequisites and a verifiable result.
- Navigation labels match user language.
- Reference content describes defaults, constraints, errors, and examples.
- Failure paths and recovery steps are documented.
- Pages identify version scope where behavior varies.
- Content does not expose secrets or recommend unsafe production defaults.
- Heading order, link text, alt text, focus behavior, contrast, and mobile overflow are acceptable.
- Search terms include common synonyms and previous product terminology when useful.
- Owners and update triggers are known for high-risk pages.
