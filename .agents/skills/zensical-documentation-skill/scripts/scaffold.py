#!/usr/bin/env python3
import argparse
from pathlib import Path

INDEX = """# {site_name}\n\nWelcome to the {site_name}.\n\n## Start here\n\n- [Installation](getting-started/installation.md)\n- [Quickstart](getting-started/quickstart.md)\n- [Concepts](concepts/index.md)\n- [Reference](reference/index.md)\n- [Troubleshooting](operations/troubleshooting.md)\n"""
PAGES = {
    "getting-started/installation.md": "# Installation\n\nTODO: Document prerequisites, supported platforms, installation steps, and verification.\n",
    "getting-started/quickstart.md": "# Quickstart\n\nTODO: Provide the shortest safe path to a verified result.\n",
    "concepts/index.md": "# Concepts\n\nTODO: Explain the product mental model and architecture.\n",
    "reference/index.md": "# Reference\n\nTODO: Link to API, CLI, SDK, and configuration reference.\n",
    "operations/troubleshooting.md": "# Troubleshooting\n\nTODO: Organize symptoms, causes, diagnostics, and resolutions.\n",
}

def main():
    p=argparse.ArgumentParser(description="Scaffold a minimal Zensical documentation project")
    p.add_argument("directory")
    p.add_argument("--site-name", default="Product Documentation")
    args=p.parse_args()
    root=Path(args.directory)
    docs=root/"docs"
    docs.mkdir(parents=True, exist_ok=True)
    config=root/"zensical.toml"
    if not config.exists():
        config.write_text(f'[project]\nsite_name = "{args.site_name.replace(chr(34), chr(39))}"\nsite_description = "Technical documentation and user guides"\n\n[project.theme]\nvariant = "modern"\n', encoding="utf-8")
    index=docs/"index.md"
    if not index.exists(): index.write_text(INDEX.format(site_name=args.site_name), encoding="utf-8")
    for rel, content in PAGES.items():
        path=docs/rel; path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists(): path.write_text(content, encoding="utf-8")
    print(f"Scaffolded {root}")

if __name__ == "__main__": main()
