#!/usr/bin/env bash
# Compiles src/input.css into styles.css using the Tailwind CSS standalone
# CLI (no Node/npm). Downloads the pinned CLI binary into .tailwindcss-cli/
# on first run; that directory is gitignored.
set -euo pipefail

UI_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TAILWIND_VERSION="v4.3.3"
CLI_DIR="$UI_DIR/.tailwindcss-cli"
CLI_BIN="$CLI_DIR/tailwindcss"

if [ ! -x "$CLI_BIN" ]; then
  case "$(uname -s)-$(uname -m)" in
    Darwin-arm64) ASSET="tailwindcss-macos-arm64" ;;
    Darwin-x86_64) ASSET="tailwindcss-macos-x64" ;;
    Linux-aarch64) ASSET="tailwindcss-linux-arm64" ;;
    Linux-x86_64) ASSET="tailwindcss-linux-x64" ;;
    *) echo "Unsupported platform: $(uname -s)-$(uname -m). Download the CLI manually from https://github.com/tailwindlabs/tailwindcss/releases/$TAILWIND_VERSION and place it at $CLI_BIN" >&2; exit 1 ;;
  esac
  mkdir -p "$CLI_DIR"
  echo "Downloading tailwindcss CLI $TAILWIND_VERSION ($ASSET)..."
  curl -fsSL -o "$CLI_BIN" "https://github.com/tailwindlabs/tailwindcss/releases/download/$TAILWIND_VERSION/$ASSET"
  chmod +x "$CLI_BIN"
fi

"$CLI_BIN" -i "$UI_DIR/src/input.css" -o "$UI_DIR/styles.css" --minify
echo "Wrote $UI_DIR/styles.css"
