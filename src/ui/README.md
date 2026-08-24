# Wayfinder local editor

A dependency-free Vanilla JS interface for editing `pyauditor` config (as dedicated forms for the common families, raw text otherwise) inside one explicitly configured local workspace, then running the pipeline against it.

## Why a local server is required

Opening `index.html` with `file://` cannot safely enumerate arbitrary Desktop files, save them back without user-mediated browser permissions, or launch `uv run pyauditor`. `server.py` provides those capabilities locally and binds to `127.0.0.1` by default.

## Requirements

- Python 3.12+
- `uv` and the `pyauditor` repository dependencies already installed

## Run

Copy this folder anywhere, then point Wayfinder to the root of the pyauditor repository:

```bash
python3 server.py --workspace "../pyauditor"
```

The browser opens at <http://127.0.0.1:8765>. Only YAML and CSS files under that repo's `configs/` — the single source of pyauditor config — are shown; the rest of the repo (tests, CI, docs) stays out of the sidebar. Saving creates a sibling `.bak` backup and uses an atomic replace.

For a repository elsewhere:

```bash
python3 server.py --workspace "/absolute/path/to/pyauditor"
```

## Golden path

1. **Pick a config family from the sidebar.** Four families get dedicated forms instead of raw YAML — you should never feel like you're editing YAML for these:
   - **INMS indicators** — grouped by indicator key; pick an agency (MinC/MTur) to render a two-part form: the shared contract (`_shared/inms-NN.yaml`) plus that agency's per-category segments (`{orgao}/inms-NN.CATEGORIA.yaml`).
   - **Categorias** — one form per agency (`{orgao}/categorias.yaml`), mapping each categoria to its INMS filter mode (`grupo_executor` with `in_values`/`catch_all_contains`, or `whole_indicator`).
   - **Datasets** — the single `_shared/datasets.yaml`, alias → CSV file + parsing options.
   - **Contract constants** — a bundle of the three small global files (`dados_contratuais.yaml`, `ajuste_inms.yaml`, `desconto_regulatório.yaml`).

   Anything else (other YAML, CSS) stays a plain-text editor.
2. **Edit fields, then Save.** The center pane tracks dirty state; Save writes the parsed form back to the same YAML file(s), with a `.bak` sibling and an atomic replace. Leaving with unsaved changes prompts a discard confirmation.
3. **Run the pipeline from the Pipeline panel.** Pick one of the 6 `pyauditor` subcommands (`bootstrap`, `measure`, `report`, `consolidate`, `split`, `run`) — the form only shows the flags that subcommand needs (competence, agency, `--strict`, `--final-month`, `--force`/`--clean` for `run`). Steps run one at a time server-side, so a failing step can be retried alone without re-running the whole pipeline.
4. **Read warnings, jump to the field that caused one.** When a job finishes, structured warnings (currently `in_values_unmatched` and `outros_leftover`, both from `categorias.yaml`) show in a floating panel. Clicking one opens the right agency's Categorias form, scrolls to the exact card, and highlights it. Warnings without a known target just show as text.
5. **Check past runs from Run history.** The Pipeline panel keeps a short, session-independent list of recent jobs (id + command + status); clicking one re-displays its output and warnings without re-running it.

To override the invocation prefix (e.g. to point at a different interpreter or a globally installed `pyauditor`), set `WAYFINDER_PIPELINE_CMD` to just the prefix — the selected subcommand, competence, and flags are appended automatically:

```bash
export WAYFINDER_PIPELINE_CMD='uv run pyauditor'
python3 server.py --workspace "/absolute/path/to/pyauditor"
```

## Rebuilding styles.css

`styles.css` is compiled from `src/input.css` by the Tailwind CSS **standalone
CLI** — no Node/npm involved. The compiled `styles.css` is committed, so most
changes to `index.html` don't require a rebuild; rerun the build when you add
Tailwind utility classes to the markup or edit `src/input.css`:

```bash
./scripts/build-css.sh
```

The first run downloads the pinned CLI binary into `.tailwindcss-cli/`
(gitignored, macOS/Linux arm64/x64 auto-detected). `src/input.css` also
carries the app's hand-written CSS verbatim, so today's Tailwind utility
layer is unused — it becomes relevant as new markup opts into utility
classes.

## Security boundaries

- Binds only to localhost unless explicitly changed.
- Restricts read/write operations to the configured workspace.
- Allows only `.yaml`, `.yml`, and `.css` files.
- Limits editable files and request bodies to 2 MiB.
- Executes an administrator-configured argument vector without a shell.
- Never exposes production data unless it is a YAML/CSS file inside the selected workspace.

Do not bind this development tool to a public network.
