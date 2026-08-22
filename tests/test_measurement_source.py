"""`engine.pipeline.measurement_source()` — o backbone resolve→valida→lê→
filtra→gates (ticket 02) usado por `engine.measure`, `sintetico`, `split` e
`cli.measure` (tickets 03-05)."""

import sys
from datetime import date
from io import StringIO
from pathlib import Path

import pytest

from pyauditor.engine.pipeline import load_config, measurement_source
from pyauditor.logging import setup_logging
from pyauditor.periodo import PeriodoAfericao

_CONFIG_YAML = """\
indicator:
  id: INMS-BACKBONE
  contractual_id: "INMS BACKBONE"
  name: Backbone

scope:
  contract: "40/2022 - Ministério da Cultura"
  orgao: MinC

source:
  csv: data.csv
  delimiter: ","
  encoding: utf-8
  period_column: "DataHoraFim"
  id_column: "Nº Solicitação"

quality_gates:
  checks:
    - type: not_null
      column: "Atendido"

calculation:
  shape: ratio
  aggregation: count_distinct
  numerator_filter:
    column: "Atendido"
    equals: "S"

target:
  operator: ">="
  value: 98.0

penalty:
  base_points: 50
  step_points: 100
  step_size_pct: 4.0
"""


def _write_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(_CONFIG_YAML, encoding="utf-8")
    return config_path


def test_resolves_reads_and_gates(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)
    (tmp_path / "data.csv").write_text(
        "Nº Solicitação,DataHoraFim,Atendido\n1,20/06/2026 10:00,S\n2,21/06/2026 10:00,\n",
        encoding="utf-8",
    )
    config = load_config(config_path)

    bundle = measurement_source(config, data_dir=tmp_path, config_path=config_path)

    assert bundle.csv_path == tmp_path / "data.csv"
    assert bundle.delimiter == ","
    assert bundle.fieldnames == ["Nº Solicitação", "DataHoraFim", "Atendido"]
    assert len(bundle.rows) == 2
    assert len(bundle.gate_report.accepted) == 1
    assert len(bundle.gate_report.rejected) == 1
    assert len(bundle.accepted_ids) == 1
    assert bundle.dropped_out_of_period is None
    assert bundle.undated_dropped is None


def test_missing_yaml_column_raises(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)
    (tmp_path / "data.csv").write_text("Nº Solicitação,DataHoraFim\n1,20/06/2026 10:00\n", encoding="utf-8")
    config = load_config(config_path)

    with pytest.raises(ValueError, match="coluna\\(s\\) referenciada"):
        measurement_source(config, data_dir=tmp_path, config_path=config_path)


def test_period_filter_counts_and_warns_once(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)
    (tmp_path / "data.csv").write_text(
        "Nº Solicitação,DataHoraFim,Atendido\n1,20/05/2026 10:00,S\n", encoding="utf-8"
    )
    config = load_config(config_path)
    periodo = PeriodoAfericao(date(2026, 6, 1), date(2026, 6, 30))
    buf = StringIO()
    setup_logging(sink=buf, level="INFO")

    try:
        bundle = measurement_source(
            config, data_dir=tmp_path, config_path=config_path, periodo=periodo
        )
    finally:
        setup_logging(sink=sys.stderr, level="INFO")

    logs = buf.getvalue()
    assert "nenhuma linha no período 01/06/2026–30/06/2026" in logs
    assert "1 linha(s) fora do período descartada(s)" in logs
    assert bundle.dropped_out_of_period == 1
    assert bundle.rows == []


def test_emit_empty_window_warning_false_suppresses_warn_not_info(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)
    (tmp_path / "data.csv").write_text(
        "Nº Solicitação,DataHoraFim,Atendido\n1,20/05/2026 10:00,S\n", encoding="utf-8"
    )
    config = load_config(config_path)
    periodo = PeriodoAfericao(date(2026, 6, 1), date(2026, 6, 30))
    buf = StringIO()
    setup_logging(sink=buf, level="INFO")

    try:
        bundle = measurement_source(
            config,
            data_dir=tmp_path,
            config_path=config_path,
            periodo=periodo,
            emit_empty_window_warning=False,
        )
    finally:
        setup_logging(sink=sys.stderr, level="INFO")

    logs = buf.getvalue()
    assert "nenhuma linha no período" not in logs
    assert "1 linha(s) fora do período descartada(s)" in logs
    assert bundle.dropped_out_of_period == 1
