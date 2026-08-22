"""Manual-entry ingestion schema for INMS 1.8, per docs/spec/inms-pipeline.md
§11.3: since no primary source defines how a desconformidade técnica gets
recorded (ticket 11), and the real /input/inms-001-08.csv is empty, this
proves a documented, human-fillable schema (`ID_Ocorrencia`, `Data`,
`Descricao`, `Codigos_Anexo_E`) round-trips correctly through `measure`.
`tests/fixtures/manual_entry_examples/inms-1.8-occurrences.csv` doubles as a
worked example of the schema.
"""

from pathlib import Path

from pyauditor.engine.pipeline import load_config, measure
from pyauditor.rom.render import render_rom

FIXTURES_DIR = Path(__file__).parent / 'fixtures' / 'manual_entry_examples'


def test_schema_round_trips_through_measure() -> None:
    config = load_config(FIXTURES_DIR / 'inms-1.8-config.yaml')

    result = measure(config, data_dir=FIXTURES_DIR)

    # OC-2026-004 has no Codigos_Anexo_E -> rejected by the not_null quality
    # gate.
    assert [row.row_id for row in result.quality_gate_report.rejected] == [
        'OC-2026-004'
    ]
    assert len(result.quality_gate_report.accepted) == 4

    # OD-52=100, max(OD-10=500, OD-20=50)=500 (multi-código, maior pontuação
    # vence), OD-30=500, OD-60=200
    assert result.calculation.memoria['total_points'] == 1300
    assert result.calculation.penalty_points == 1300.0
    assert result.calculation.conforms is False

    occurrences = result.calculation.memoria['occurrences']
    assert isinstance(occurrences, list)
    assert [o['occurrence_id'] for o in occurrences] == [
        'OC-2026-001',
        'OC-2026-002',
        'OC-2026-003',
        'OC-2026-005',
    ]
    multi_code_occurrence = occurrences[1]
    assert (
        multi_code_occurrence['catalog_id'] == 'OD-10'
    )  # 500 > 50, maior pontuação vence


def test_schema_produces_a_valid_rom_and_lists_rejection_reason() -> None:
    config = load_config(FIXTURES_DIR / 'inms-1.8-config.yaml')
    result = measure(config, data_dir=FIXTURES_DIR)

    rom = render_rom(result)

    assert '# ROM — INMS 1.08' in rom
    assert 'OC-2026-004' in rom
    assert 'nulo/vazio' in rom
    assert 'OD-52' in rom
    assert 'Σ Pontos_NMS = 1300' in rom
