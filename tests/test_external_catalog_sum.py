"""INMS 1.8 (`external_catalog_sum`): real `/input/inms-001-08.csv` is empty
(header only, same open dataset-schema question as INMS 1.10 — ticket 05),
so its acceptance test only proves the pipeline runs against the real file.
The catalog lookup, max-points-wins dedup, and sum are proven by a synthetic
fixture instead.
"""

from pathlib import Path

import pytest

from pyauditor.config.catalog import load_anexo_e_catalog
from pyauditor.config.models import ExternalCatalogSumAcceptanceExpected
from pyauditor.engine.pipeline import load_config, measure
from pyauditor.rom.render import render_rom

REPO_ROOT = Path(__file__).parent.parent
CONFIG_PATH = REPO_ROOT / 'tests' / 'fixtures' / 'configs' / 'inms-1.8.yaml'
INPUT_DIR = REPO_ROOT / 'input'


def test_catalog_loads_106_items_with_expected_range() -> None:
    catalog = load_anexo_e_catalog()

    assert len(catalog) == 106
    assert catalog['OD-01'].pontos == 20000
    assert catalog['OD-106'].categoria == 'Servidores de Aplicação'
    assert min(item.pontos for item in catalog.values()) == 50
    assert max(item.pontos for item in catalog.values()) == 20000


@pytest.mark.skipif(
    not (INPUT_DIR / 'inms-001-08.csv').exists(),
    reason='production data (/input) not present locally',
)
def test_inms_1_8_matches_acceptance_test() -> None:
    config = load_config(CONFIG_PATH)
    assert config.acceptance_test is not None
    expected = config.acceptance_test.expected
    assert isinstance(expected, ExternalCatalogSumAcceptanceExpected)

    result = measure(config, data_dir=INPUT_DIR)

    assert result.calculation.memoria['total_points'] == expected.total_points
    assert result.calculation.memoria['occurrences'] == []
    assert result.calculation.conforms == expected.conforms
    assert result.calculation.penalty_points == pytest.approx(
        expected.penalty_points
    )


@pytest.mark.skipif(
    not (INPUT_DIR / 'inms-001-08.csv').exists(),
    reason='production data (/input) not present locally',
)
def test_inms_1_8_rom_renders_without_target_section() -> None:
    config = load_config(CONFIG_PATH)
    result = measure(config, data_dir=INPUT_DIR)

    rom = render_rom(result)

    assert '# ROM — INMS 1.08' in rom
    assert '| Ocorrência | Item Anexo E | Descrição | Pontos |' in rom
    assert 'não aplicável' in rom


def test_external_catalog_sum_applies_max_points_wins_dedup(
    tmp_path: Path,
) -> None:
    config_yaml = """
indicator:
  id: INMS-TEST-1.8
  contractual_id: "INMS TEST 1.8"
  name: Indicador sintético de desconformidades

scope:
  contract: "40/2022 - Ministério da Cultura"
  orgao: MinC

source:
  csv: data.csv
  delimiter: ";"
  encoding: utf-8

quality_gates:
  checks: []

calculation:
  shape: external_catalog_sum
  occurrence_id_column: "Ocorrencia"
  catalog_codes_column: "Codigos"
  catalog_codes_separator: ","
"""
    (tmp_path / 'config.yaml').write_text(config_yaml, encoding='utf-8')
    (tmp_path / 'data.csv').write_text(
        'Ocorrencia;Codigos\n'
        'OC-001;OD-52\n'  # 100 pontos
        'OC-002;OD-01\n'  # 20000 pontos
        'OC-003;OD-02,OD-03\n'  # multi-enquadrada: max(5000, 3000) = 5000
        'OC-004;\n'  # nenhum código -> ignorada
        'OC-005;OD-999\n',  # código inexistente no catálogo -> ignorada
        encoding='utf-8',
    )

    config = load_config(tmp_path / 'config.yaml')
    result = measure(config, data_dir=tmp_path)

    assert result.calculation.memoria['total_points'] == 100 + 20000 + 5000
    assert result.calculation.penalty_points == pytest.approx(25100.0)
    assert result.calculation.conforms is False

    occurrences = result.calculation.memoria['occurrences']
    assert isinstance(occurrences, list)
    assert [o['occurrence_id'] for o in occurrences] == [
        'OC-001',
        'OC-002',
        'OC-003',
    ]
    assert (
        occurrences[2]['catalog_id'] == 'OD-02'
    )  # maior pontuação vence sobre OD-03
    assert occurrences[2]['pontos'] == 5000


def test_external_catalog_sum_conforms_when_no_occurrences_matched(
    tmp_path: Path,
) -> None:
    config_yaml = """
indicator:
  id: INMS-TEST-1.8-VAZIO
  contractual_id: "INMS TEST 1.8 vazio"
  name: Indicador sintético sem ocorrências

scope:
  contract: "40/2022 - Ministério da Cultura"
  orgao: MinC

source:
  csv: data.csv
  delimiter: ";"
  encoding: utf-8

quality_gates:
  checks: []

calculation:
  shape: external_catalog_sum
  occurrence_id_column: "Ocorrencia"
  catalog_codes_column: "Codigos"
"""
    (tmp_path / 'config.yaml').write_text(config_yaml, encoding='utf-8')
    (tmp_path / 'data.csv').write_text('Ocorrencia;Codigos\n', encoding='utf-8')

    config = load_config(tmp_path / 'config.yaml')
    result = measure(config, data_dir=tmp_path)

    assert result.calculation.memoria == {'occurrences': [], 'total_points': 0}
    assert result.calculation.conforms is True
    assert result.calculation.penalty_points == pytest.approx(0.0)
