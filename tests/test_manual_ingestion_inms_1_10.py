"""Manual-entry ingestion schema for INMS 1.10, per docs/spec/inms-pipeline.md
§2: since no primary source defines how a recommended/implemented security
control gets recorded (ticket 05), and the real /input/inms-001-10.csv is
empty, this proves a documented, human-fillable schema (`ID_Controle`,
`Framework`, `Descricao`, `Implantado`) round-trips correctly through
`measure`. `tests/fixtures/manual_entry_examples/inms-1.10-controles.csv`
doubles as a worked example of the schema.
"""

from pathlib import Path

from pyauditor.engine.pipeline import load_config, measure
from pyauditor.rom.render import render_rom

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "manual_entry_examples"


def test_schema_round_trips_through_measure() -> None:
    config = load_config(FIXTURES_DIR / "inms-1.10-config.yaml")

    result = measure(config, data_dir=FIXTURES_DIR)

    # CTRL-06 has no "Implantado" value -> rejected by the in_set quality gate.
    assert [row.row_id for row in result.quality_gate_report.rejected] == ["CTRL-06"]
    assert len(result.quality_gate_report.accepted) == 5

    # QRC = 5 accepted controls; QCSI = 3 implemented (CTRL-01/02/03); CNI = 2
    assert result.calculation.memoria == {"QRC": 5, "QCSI": 3, "CNI": 2}
    assert result.calculation.penalty_points == 2000.0
    assert result.calculation.result_pct == 60.0
    assert result.calculation.conforms is False


def test_schema_produces_a_valid_rom_and_lists_rejection_reason() -> None:
    config = load_config(FIXTURES_DIR / "inms-1.10-config.yaml")
    result = measure(config, data_dir=FIXTURES_DIR)

    rom = render_rom(result)

    assert "# ROM — INMS 1.10" in rom
    assert "CTRL-06" in rom
    assert "fora do conjunto permitido" in rom
    assert "QRC (recomendados): 5" in rom
    assert "QCSI (implantados): 3" in rom
    assert "CNI = QRC − QCSI = 2" in rom
