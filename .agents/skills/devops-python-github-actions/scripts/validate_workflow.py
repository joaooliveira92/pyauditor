#!/usr/bin/env python3
"""Baseline policy checks for GitHub Actions workflow files."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ACTION_RE = re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)", re.MULTILINE)
FULL_SHA_RE = re.compile(r"^[^@]+@[0-9a-fA-F]{40}$")


def validate(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    findings: list[str] = []
    if "permissions:" not in text:
        findings.append("missing explicit permissions")
    if "timeout-minutes:" not in text:
        findings.append("missing timeout-minutes")
    if "pull_request_target:" in text:
        findings.append("pull_request_target requires a manual trust-boundary review")
    for action in ACTION_RE.findall(text):
        if action.startswith("./") or action.startswith("docker://"):
            continue
        if not FULL_SHA_RE.fullmatch(action):
            findings.append(f"action is not pinned to a full SHA: {action}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workflow", type=Path)
    args = parser.parse_args()
    if not args.workflow.is_file():
        print(f"error: file not found: {args.workflow}", file=sys.stderr)
        return 2
    findings = validate(args.workflow)
    if findings:
        for finding in findings:
            print(f"WARN: {finding}")
        return 1
    print("OK: baseline workflow checks passed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
