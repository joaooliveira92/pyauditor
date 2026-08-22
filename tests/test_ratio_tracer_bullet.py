"""INMS 1.1 end-to-end: config parse -> quality gates -> `ratio` strategy ->
ROM.

Uses the real production CSV in /input (git-ignored, PII — see
docs/spec/inms-pipeline.md §8). Skips if that data isn't present locally.
"""

from pathlib import Path

import pytest

from pyauditor.config.models import RatioAcceptanceExpected
from pyauditor.engine.pipeline import load_config, measure
from pyauditor.rom.render import render_rom

REPO_ROOT = Path(__file__).parent.parent
CONFIG_PATH = REPO_ROOT / 'tests' / 'fixtures' / 'configs' / 'inms-1.1.yaml'
INPUT_DIR = REPO_ROOT / 'input'

pytestmark = pytest.mark.skipif(
    not (INPUT_DIR / 'inms-001-01.csv').exists(),
    reason='production data (/input) not present locally',
)


def test_inms_1_1_matches_acceptance_test() -> None:
    config = load_config(CONFIG_PATH)
    assert config.acceptance_test is not None
    expected = config.acceptance_test.expected
    assert isinstance(expected, RatioAcceptanceExpected)

    result = measure(config, data_dir=INPUT_DIR)

    assert result.calculation.memoria['numerator'] == expected.numerator
    assert result.calculation.memoria['denominator'] == expected.denominator
    assert result.calculation.result_pct == pytest.approx(
        expected.result_pct, abs=0.01
    )
    assert result.calculation.conforms == expected.conforms
    assert result.calculation.penalty_points == pytest.approx(
        expected.penalty_points, abs=0.01
    )


def test_inms_1_1_rom_renders_expected_sections() -> None:
    config = load_config(CONFIG_PATH)
    result = measure(config, data_dir=INPUT_DIR)

    rom = render_rom(result)

    assert '# ROM — INMS 1.01' in rom
    assert '## Identificação' in rom
    assert '## Linhas aprovadas pelo quality gate' in rom
    assert '## Rejeições' in rom
    assert '## Memória de cálculo' in rom
    assert (
        '## Ressalva interpretativa' in rom
    )  # 171/175 falls short of 98% -> penalty > 0
    assert '## Resultado vs meta' in rom
    assert '## Responsáveis' in rom
    assert 'não conforme' in rom
