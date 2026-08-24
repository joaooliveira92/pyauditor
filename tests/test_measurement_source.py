"""`engine.pipeline.measurement_source()` — o backbone resolve→valida→lê→
filtra→gates (ticket 02) usado por `engine.measure`, `sintetico`, `split` e
`cli.measure` (tickets 03-05)."""

import sys
from datetime import date
from io import StringIO
from pathlib import Path
from typing import cast

import pytest

from pyauditor.engine.pipeline import load_config, measure, measurement_source
from pyauditor.engine.strategies._memoria import RatioMemoria
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
    config_path = tmp_path / 'config.yaml'
    config_path.write_text(_CONFIG_YAML, encoding='utf-8')
    return config_path


def test_resolves_reads_and_gates(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)
    (tmp_path / 'data.csv').write_text(
        'Nº '
        'Solicitação,DataHoraFim,Atendido\n1,20/06/2026 '
        '10:00,S\n2,21/06/2026 '
        '10:00,\n',
        encoding='utf-8',
    )
    config = load_config(config_path)

    bundle = measurement_source(
        config, data_dir=tmp_path, config_path=config_path
    )

    assert bundle.csv_path == tmp_path / 'data.csv'
    assert bundle.delimiter == ','
    assert bundle.fieldnames == ['Nº Solicitação', 'DataHoraFim', 'Atendido']
    assert len(bundle.rows) == 2
    assert len(bundle.gate_report.accepted) == 1
    assert len(bundle.gate_report.rejected) == 1
    assert len(bundle.accepted_ids) == 1
    assert bundle.dropped_out_of_period is None
    assert bundle.undated_dropped is None


def test_missing_yaml_column_raises(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)
    body = 'Nº Solicitação,DataHoraFim\n1,20/06/2026 10:00\n'
    (tmp_path / 'data.csv').write_text(body, encoding='utf-8')
    config = load_config(config_path)

    with pytest.raises(ValueError, match='coluna\\(s\\) referenciada'):
        measurement_source(config, data_dir=tmp_path, config_path=config_path)


def test_empty_csv_skips_missing_column_check_warns_and_measures_0_0(
    tmp_path: Path,
) -> None:
    """Competência legitima vazia (CSV só com cabeçalho, zero linhas de dados)
    não é falha técnica: as colunas referenciadas no YAML nem existem no header
    e não há dado para computar contra elas — o resultado é 0/0 sem base para
    glosa (caso real INMS 1.3: zero projetos confirmado pela fiscalização — ver
    tests/fixtures/configs/inms-1.3.yaml). O backbone deve WARN (não levantar)
    e `measure` deve retornar conforms com 0 pontos."""
    config_path = _write_config(tmp_path)
    # Header sem a coluna "Atendido" referenciada no YAML, e zero linhas.
    (tmp_path / 'data.csv').write_text(
        'Nº Solicitação,DataHoraFim\n', encoding='utf-8'
    )
    config = load_config(config_path)
    buf = StringIO()
    setup_logging(sink=buf, level='INFO')

    try:
        bundle = measurement_source(
            config, data_dir=tmp_path, config_path=config_path
        )
        result = measure(config, data_dir=tmp_path, config_path=config_path)
    finally:
        setup_logging(sink=sys.stderr, level='INFO')

    assert bundle.rows == []
    logs = buf.getvalue()
    assert 'coluna(s) referenciada(s) no YAML não existe(m)' in logs
    assert 'Atendido' in logs
    assert result.calculation.memoria == RatioMemoria(
        numerator=0.0, denominator=0.0
    )
    assert result.calculation.conforms is True
    assert result.calculation.penalty_points == pytest.approx(0.0)
    assert result.hard_failure is False


def test_period_filter_counts_and_warns_once(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)
    (tmp_path / 'data.csv').write_text(
        'Nº Solicitação,DataHoraFim,Atendido\n1,20/05/2026 10:00,S\n',
        encoding='utf-8',
    )
    config = load_config(config_path)
    periodo = PeriodoAfericao(date(2026, 6, 1), date(2026, 6, 30))
    buf = StringIO()
    setup_logging(sink=buf, level='INFO')

    try:
        bundle = measurement_source(
            config, data_dir=tmp_path, config_path=config_path, periodo=periodo
        )
    finally:
        setup_logging(sink=sys.stderr, level='INFO')

    logs = buf.getvalue()
    assert 'nenhuma linha no período 01/06/2026–30/06/2026' in logs
    assert '1 linha(s) fora do período descartada(s)' in logs
    assert bundle.dropped_out_of_period == 1
    assert bundle.rows == []


def test_ragged_rows_are_counted_not_silently_dropped(tmp_path: Path) -> None:
    """Fila com campos além do cabeçalho (campo livre deslocando colunas):
    `raw.ragged_rows`/`bundle.ragged_rows` contam em vez de só truncar."""
    config_path = _write_config(tmp_path)
    (tmp_path / 'data.csv').write_text(
        'Nº Solicitação,DataHoraFim,Atendido\n'
        '1,20/06/2026 10:00,S\n'
        '2,21/06/2026 10:00,S,EXTRA\n',
        encoding='utf-8',
    )
    config = load_config(config_path)

    bundle = measurement_source(
        config, data_dir=tmp_path, config_path=config_path
    )
    result = measure(config, data_dir=tmp_path, config_path=config_path)

    assert bundle.ragged_rows == 1
    assert result.ragged_rows == 1
    assert len(bundle.rows) == 2


_SUM_CONFIG_YAML = """\
indicator:
  id: INMS-SUM
  contractual_id: "INMS SUM"
  name: Sum com coluna numérica

scope:
  contract: "40/2022 - Ministério da Cultura"
  orgao: MinC

source:
  csv: data.csv
  delimiter: ","
  encoding: utf-8

quality_gates:
  checks: []

calculation:
  shape: ratio
  aggregation: sum
  sum_numerator_column: "Valor"
  sum_denominator_extra_column: "Base"

target:
  operator: ">="
  value: 90.0

penalty:
  base_points: 0
  step_points: 10
  step_size_pct: 1.0
"""


def test_unparseable_numeric_cells_are_counted(tmp_path: Path) -> None:
    """Célula numérica ilegível (`parse_decimal` → nan) é ignorada no cálculo
    mas fica contada na trilha de auditoria (`unparseable_numerics`), em vez
    de sumir em silêncio."""
    config_path = tmp_path / 'config.yaml'
    config_path.write_text(_SUM_CONFIG_YAML, encoding='utf-8')
    (tmp_path / 'data.csv').write_text(
        'Valor,Base\n10,100\nabc,100\n',
        encoding='utf-8',
    )
    config = load_config(config_path)

    bundle = measurement_source(
        config, data_dir=tmp_path, config_path=config_path
    )
    result = measure(config, data_dir=tmp_path, config_path=config_path)

    assert bundle.unparseable_numerics == 1
    assert result.unparseable_numerics == 1
    # `abc` descartado -> só o 10 entra no numerador.
    memoria = cast(RatioMemoria, result.calculation.memoria)
    assert memoria['numerator'] == 10.0


def test_measurement_source_delimiter_ambiguous_strict_raises(
    tmp_path: Path,
) -> None:
    """Delimiter ambíguo (ambos candidatos presentes na amostra) falha em
    `strict` em vez de adivinhar — aferição não pode aceitar parsing de
    baixo custo sobre dado ilegível."""
    config_path = tmp_path / 'config.yaml'
    config_path.write_text(
        _CONFIG_YAML.replace('delimiter: ","', 'delimiter: ";"'),
        encoding='utf-8',
    )
    (tmp_path / 'data.csv').write_text(
        'Nº Solicitação,DataHoraFim;Atendido\n1,20/06/2026 10:00;S\n',
        encoding='utf-8',
    )
    config = load_config(config_path)

    with pytest.raises(ValueError, match='delimiter ambíguo'):
        measurement_source(
            config, data_dir=tmp_path, config_path=config_path, strict=True
        )
    # modo normal: mantém o configurado com warning, não falha
    bundle = measurement_source(
        config, data_dir=tmp_path, config_path=config_path
    )
    assert bundle.delimiter == ';'
    """Chamadores que logam com seu próprio contexto estruturado (`split`,
    via `log_event`) desligam ambos e usam as contagens do `SourceBundle`."""
    config_path = _write_config(tmp_path)
    (tmp_path / 'data.csv').write_text(
        'Nº Solicitação,DataHoraFim,Atendido\n1,20/05/2026 10:00,S\n',
        encoding='utf-8',
    )
    config = load_config(config_path)
    periodo = PeriodoAfericao(date(2026, 6, 1), date(2026, 6, 30))
    buf = StringIO()
    setup_logging(sink=buf, level='INFO')

    try:
        bundle = measurement_source(
            config,
            data_dir=tmp_path,
            config_path=config_path,
            periodo=periodo,
            emit_period_filter_logs=False,
        )
    finally:
        setup_logging(sink=sys.stderr, level='INFO')

    logs = buf.getvalue()
    assert 'nenhuma linha no período' not in logs
    assert '1 linha(s) fora do período descartada(s)' not in logs
    assert bundle.dropped_out_of_period == 1
    assert bundle.dropped_out_of_period == 1
