# Wayfinder local editor

A dependency-free Vanilla JS interface for editing `.yaml`, `.yml`, and `.css` files inside one explicitly configured local workspace, then running the `pyauditor` pipeline.

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

The browser opens at <http://127.0.0.1:8765>. Only YAML and CSS files under that workspace are shown. Saving creates a sibling `.bak` backup and uses an atomic replace.

For a repository elsewhere:

```bash
python3 server.py --workspace "/absolute/path/to/pyauditor"
```

The Pipeline panel can run any of the 6 `pyauditor` subcommands (`bootstrap`, `measure`, `report`, `consolidate`, `split`, `run`) one at a time, so a failing step can be retried alone.

INMS indicator configs are not edited as raw YAML: the sidebar groups `_shared/inms-NN.yaml` + `{orgao}/inms-NN.CATEGORIA.yaml` files under each indicator, and the center pane renders them as a two-part form (shared contract, then per-agency segments). Editing a field writes the parsed YAML back to the same files on save. Non-INMS YAML and CSS files remain raw-text edits.

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
