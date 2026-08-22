#!/usr/bin/env python3
"""Validate the stable core of a testing evolution state file."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate(data: Any) -> None:
    require(isinstance(data, dict), 'state must be a JSON object')
    require(data.get('schema_version') == 1, 'schema_version must equal 1')
    require(isinstance(data.get('project'), str) and bool(data['project']), 'project must be a non-empty string')
    baseline = data.get('baseline')
    require(isinstance(baseline, dict), 'baseline must be an object')
    for key in ('tests', 'failures', 'skipped'):
        value = baseline.get(key)
        require(value is None or (isinstance(value, int) and value >= 0), f'baseline.{key} must be null or a non-negative integer')
    coverage = baseline.get('branch_coverage_percent')
    require(coverage is None or (isinstance(coverage, int | float) and 0 <= coverage <= 100), 'branch coverage must be null or between 0 and 100')
    for key in ('completed_objectives', 'known_risks'):
        value = data.get(key)
        require(isinstance(value, list) and all(isinstance(item, str) for item in value), f'{key} must be a string array')
    require(data.get('next_objective') is None or isinstance(data.get('next_objective'), str), 'next_objective must be null or a string')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('state', type=Path)
    args = parser.parse_args()
    try:
        validate(json.loads(args.state.read_text(encoding='utf-8')))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f'ERROR: {exc}')
        return 1
    print('OK: testing progress state is valid')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
