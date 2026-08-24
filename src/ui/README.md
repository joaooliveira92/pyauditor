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

To override the pipeline command while preserving the required placeholders:

```bash
export WAYFINDER_PIPELINE_CMD='uv run pyauditor run {competence} --orgao {agency}'
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
