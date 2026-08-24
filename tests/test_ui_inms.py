from __future__ import annotations

from pathlib import Path

import pytest

from ui.inms import discover, read_indicator, save_indicator

_SHARED = """\
indicator:
  id: INMS-01
  contractual_id: INMS 1.1
  name: Incidentes atendidos dentro do prazo
source:
  dataset: incidentes
  period_column: DataHoraSolicitacao
quality_gates:
  checks:
  - type: not_null
    column: DataHoraFim
calculation:
  shape: ratio
  aggregation: count_distinct
  numerator_filter:
    column: No prazo
    equals: S
target:
  operator: '>='
  value: 98.0
"""

_SEGMENT = """\
indicator:
  id: INMS-01.{cat}
  contractual_id: INMS 1.1
  name: Incidentes atendidos dentro do prazo
scope:
  orgao: {orgao}
source:
  csv: _split/1.1/{cat}.csv
  id_column: Nº Solicitacao
  period_column: DataHoraSolicitacao
quality_gates:
  checks: []
calculation:
  shape: ratio
  aggregation: count_distinct
  numerator_filter:
    column: No prazo
    equals: S
target:
  operator: '>='
  value: 98.0
"""


def make_workspace(tmp_path: Path) -> Path:
    shared = tmp_path / 'configs' / '_shared'
    shared.mkdir(parents=True)
    (shared / 'inms-01.yaml').write_text(_SHARED, encoding='utf-8')
    for orgao in ('MinC', 'MTur'):
        org_dir = tmp_path / 'configs' / orgao
        org_dir.mkdir(parents=True)
        for cat in ('ATENDIMENTO_N1', 'ATENDIMENTO_N2'):
            text = _SEGMENT.format(cat=cat, orgao=orgao)
            (org_dir / f'inms-01.{cat}.yaml').write_text(text, encoding='utf-8')
    return tmp_path


def test_discover_groups_shared_and_per_orgao_segments(
    tmp_path: Path,
) -> None:
    workspace = make_workspace(tmp_path)

    docs = discover(workspace)

    assert [d.key for d in docs] == ['INMS-01']
    doc = docs[0]
    assert doc.name == 'Incidentes atendidos dentro do prazo'
    assert doc.shared_rel == 'configs/_shared/inms-01.yaml'
    assert doc.orgaos == ('MinC', 'MTur')
    assert [(s.orgao, s.category) for s in doc.segments] == [
        ('MinC', 'ATENDIMENTO_N1'),
        ('MinC', 'ATENDIMENTO_N2'),
        ('MTur', 'ATENDIMENTO_N1'),
        ('MTur', 'ATENDIMENTO_N2'),
    ]


def test_read_indicator_returns_shared_and_per_orgao_segments(
    tmp_path: Path,
) -> None:
    workspace = make_workspace(tmp_path)

    doc = read_indicator(workspace, 'INMS-01', 'MinC')

    assert doc['key'] == 'INMS-01'
    assert doc['orgao'] == 'MinC'
    assert doc['shared']['config']['indicator']['id'] == 'INMS-01'
    assert 'scope' not in doc['shared']['config']
    categories = [s['category'] for s in doc['segments']]
    assert categories == ['ATENDIMENTO_N1', 'ATENDIMENTO_N2']
    assert doc['segments'][0]['config']['scope']['orgao'] == 'MinC'


def test_save_indicator_round_trips_shared_without_injecting_scope(
    tmp_path: Path,
) -> None:
    workspace = make_workspace(tmp_path)
    doc = read_indicator(workspace, 'INMS-01', 'MinC')
    doc['shared']['config']['target']['value'] = 99.0

    save_indicator(workspace, doc)

    written = read_indicator(workspace, 'INMS-01', 'MinC')
    assert written['shared']['config']['target']['value'] == 99.0
    assert 'scope' not in written['shared']['config']
    segment_text = (
        workspace / 'configs/MinC/inms-01.ATENDIMENTO_N1.yaml'
    ).read_text(encoding='utf-8')
    assert 'orgao: MinC' in segment_text


def test_save_indicator_rejects_invalid_config(
    tmp_path: Path,
) -> None:
    workspace = make_workspace(tmp_path)
    doc = read_indicator(workspace, 'INMS-01', 'MinC')
    doc['shared']['config']['target']['value'] = 'not-a-number'

    with pytest.raises(ValueError):
        save_indicator(workspace, doc)


def test_save_indicator_rejects_path_escaping_workspace(
    tmp_path: Path,
) -> None:
    workspace = make_workspace(tmp_path)
    doc = read_indicator(workspace, 'INMS-01', 'MinC')
    doc['shared']['path'] = '../../outside.yaml'

    with pytest.raises(ValueError):
        save_indicator(workspace, doc)


def test_discover_skips_non_inms_yaml(tmp_path: Path) -> None:
    (tmp_path / 'datasets.yaml').write_text('a: 1\n', encoding='utf-8')

    docs = discover(tmp_path)

    assert docs == []
