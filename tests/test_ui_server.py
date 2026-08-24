from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from ui.server import App, Handler

_SHARED = """\
indicator:
  id: INMS-01
  contractual_id: INMS 1.1
  name: Incidentes atendidos dentro do prazo
source:
  dataset: incidentes
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

_SEGMENT = """\
indicator:
  id: INMS-01.ATENDIMENTO_N1
  contractual_id: INMS 1.1
  name: Incidentes atendidos dentro do prazo
scope:
  orgao: {orgao}
source:
  csv: _split/1.1/ATENDIMENTO_N1.csv
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
        (org_dir / 'inms-01.ATENDIMENTO_N1.yaml').write_text(
            _SEGMENT.format(orgao=orgao), encoding='utf-8'
        )
    return tmp_path


@pytest.fixture()
def base_url(tmp_path: Path) -> Iterator[str]:
    Handler.app = App(make_workspace(tmp_path), '')
    Handler.web_root = Path(__file__).resolve().parent.parent / 'src' / 'ui'
    server_obj = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    port = server_obj.server_address[1]
    thread = threading.Thread(
        target=server_obj.serve_forever, daemon=True
    )
    thread.start()
    yield f'http://127.0.0.1:{port}'
    server_obj.shutdown()
    thread.join()


def _get(url: str) -> dict:
    with urlopen(url, timeout=5) as response:
        return json.loads(response.read())


def test_indicators_lists_grouped_indicators(base_url: str) -> None:
    data = _get(f'{base_url}/api/indicators')
    assert [i['key'] for i in data['indicators']] == ['INMS-01']
    entry = data['indicators'][0]
    assert entry['orgaos'] == ['MinC', 'MTur']
    assert len(entry['segments']) == 2


def test_indicator_get_returns_shared_and_segments(base_url: str) -> None:
    doc = _get(f'{base_url}/api/indicator?key=INMS-01&orgao=MinC')
    assert doc['shared']['config']['indicator']['id'] == 'INMS-01'
    assert [s['category'] for s in doc['segments']] == ['ATENDIMENTO_N1']


def test_indicator_put_saves_and_validates(base_url: str) -> None:
    doc = _get(f'{base_url}/api/indicator?key=INMS-01&orgao=MinC')
    doc['shared']['config']['target']['value'] = 99.0
    request = Request(
        f'{base_url}/api/indicator',
        data=json.dumps(doc).encode(),
        headers={'Content-Type': 'application/json'},
        method='PUT',
    )
    with urlopen(request, timeout=5) as response:
        assert json.loads(response.read()) == {'saved': True}

    reloaded = _get(f'{base_url}/api/indicator?key=INMS-01&orgao=MinC')
    assert reloaded['shared']['config']['target']['value'] == 99.0


def test_indicator_put_rejects_invalid_config(base_url: str) -> None:
    doc = _get(f'{base_url}/api/indicator?key=INMS-01&orgao=MinC')
    doc['shared']['config']['target']['value'] = 'oops'
    request = Request(
        f'{base_url}/api/indicator',
        data=json.dumps(doc).encode(),
        headers={'Content-Type': 'application/json'},
        method='PUT',
    )
    with pytest.raises(HTTPError) as excinfo:
        urlopen(request, timeout=5)
    assert excinfo.value.code == 400
