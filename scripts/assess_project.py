#!/usr/bin/env python3
"""Gera inventário determinístico de saúde de testes do repo."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path


def count_matching_files(pattern: str) -> int:
    return sum(1 for path in Path('.').glob(pattern) if path.is_file())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--output', type=Path, default=Path('weekly-testing-assessment.json')
    )
    args = parser.parse_args()
    data = {
        'schema_version': 1,
        'generated_at': datetime.now(UTC).isoformat(),
        'python_sources': count_matching_files('src/**/*.py'),
        'test_files': count_matching_files('tests/**/test_*.py'),
        'acceptance_test_files': count_matching_files(
            'tests/test_*acceptance*.py'
        ),
        'coverage_xml_present': Path('coverage.xml').is_file(),
        'junit_xml_present': Path('junit.xml').is_file(),
        'progress_state_present': Path(
            '.testing-progress/state.json'
        ).is_file(),
    }
    args.output.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    print(f'Wrote {args.output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
