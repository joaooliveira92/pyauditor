from __future__ import annotations

import json
import sys
import threading
import time
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


_CATEGORIAS = """\
categorias:
  ATENDIMENTO_N1:
    label: "Atendimento Remoto"
    inms:
      "1.1": {mode: grupo_executor, in_values: ["A"]}
"""


def make_workspace(tmp_path: Path) -> Path:
    shared = tmp_path / 'configs' / '_shared'
    shared.mkdir(parents=True)
    (shared / 'inms-01.yaml').write_text(_SHARED, encoding='utf-8')
    (shared / 'datasets.yaml').write_text(
        'datasets:\n  telefonemas:\n    file: inms-11.csv\n',
        encoding='utf-8',
    )
    for orgao in ('MinC', 'MTur'):
        org_dir = tmp_path / 'configs' / orgao
        org_dir.mkdir(parents=True)
        (org_dir / 'inms-01.ATENDIMENTO_N1.yaml').write_text(
            _SEGMENT.format(orgao=orgao), encoding='utf-8'
        )
        (org_dir / 'categorias.yaml').write_text(
            _CATEGORIAS, encoding='utf-8'
        )
    (tmp_path / 'configs' / 'dados_contratuais.yaml').write_text(
        'Fator-K máximo: "2,35"\n', encoding='utf-8'
    )
    (tmp_path / 'configs' / 'ajuste_inms.yaml').write_text(
        'formula: "A"\ndescricao: "B"\n', encoding='utf-8'
    )
    (tmp_path / 'configs' / 'desconto_regulatório.yaml').write_text(
        'formula: "C"\ndescricao: "D"\n', encoding='utf-8'
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


def test_categoria_get_returns_orgao_doc(base_url: str) -> None:
    doc = _get(f'{base_url}/api/categoria?orgao=MinC')
    assert doc['orgao'] == 'MinC'
    assert doc['config']['categorias']['ATENDIMENTO_N1']['label'] == (
        'Atendimento Remoto'
    )


def test_categoria_put_saves_and_validates(base_url: str) -> None:
    doc = _get(f'{base_url}/api/categoria?orgao=MinC')
    doc['config']['categorias']['ATENDIMENTO_N1']['inms']['1.1'][
        'in_values'
    ] = ['B']
    request = Request(
        f'{base_url}/api/categoria',
        data=json.dumps(doc).encode(),
        headers={'Content-Type': 'application/json'},
        method='PUT',
    )
    with urlopen(request, timeout=5) as response:
        assert json.loads(response.read()) == {'saved': True}

    reloaded = _get(f'{base_url}/api/categoria?orgao=MinC')
    assert reloaded['config']['categorias']['ATENDIMENTO_N1']['inms'][
        '1.1'
    ]['in_values'] == ['B']


def test_datasets_get_and_put_round_trip(base_url: str) -> None:
    doc = _get(f'{base_url}/api/datasets')
    assert doc['datasets']['telefonemas']['file'] == 'inms-11.csv'
    doc['datasets']['telefonemas']['delimiter'] = ','
    request = Request(
        f'{base_url}/api/datasets',
        data=json.dumps(doc).encode(),
        headers={'Content-Type': 'application/json'},
        method='PUT',
    )
    with urlopen(request, timeout=5) as response:
        assert json.loads(response.read()) == {'saved': True}

    reloaded = _get(f'{base_url}/api/datasets')
    assert reloaded['datasets']['telefonemas']['delimiter'] == ','


def test_contrato_get_and_put_round_trip(base_url: str) -> None:
    doc = _get(f'{base_url}/api/contrato')
    assert doc['ajuste_inms']['config']['formula'] == 'A'
    doc['ajuste_inms']['config']['formula'] = 'A2'
    request = Request(
        f'{base_url}/api/contrato',
        data=json.dumps(doc).encode(),
        headers={'Content-Type': 'application/json'},
        method='PUT',
    )
    with urlopen(request, timeout=5) as response:
        assert json.loads(response.read()) == {'saved': True}

    reloaded = _get(f'{base_url}/api/contrato')
    assert reloaded['ajuste_inms']['config']['formula'] == 'A2'


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


def _run_pipeline_server(
    tmp_path: Path, pipeline_template: str
) -> Iterator[str]:
    Handler.app = App(make_workspace(tmp_path), pipeline_template)
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


def _post_and_wait(base_url: str, payload: dict) -> dict:
    request = Request(
        f'{base_url}/api/pipeline',
        data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    with urlopen(request, timeout=5) as response:
        job_id = json.loads(response.read())['job_id']

    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        status = _get(f'{base_url}/api/pipeline/{job_id}')
        if status['status'] != 'running':
            return status
        time.sleep(0.05)
    raise TimeoutError('pipeline job did not finish in time')


def test_pipeline_run_exposes_warnings_from_json_summary(
    tmp_path: Path,
) -> None:
    fake_pipeline = tmp_path / 'fake_pipeline.py'
    fake_pipeline.write_text(
        'import json, sys\n'
        'print("some progress log line", file=sys.stderr)\n'
        'print(json.dumps({"warnings": [{"code": "in_values_unmatched"}]}))\n',
        encoding='utf-8',
    )
    template = f'{sys.executable} {fake_pipeline}'
    gen = _run_pipeline_server(tmp_path, template)
    base_url = next(gen)
    try:
        status = _post_and_wait(
            base_url,
            {
                'command': 'run',
                'competence': '2026-01',
                'agency': 'MinC',
            },
        )
        assert status['status'] == 'succeeded'
        assert status['warnings'] == [{'code': 'in_values_unmatched'}]
    finally:
        next(gen, None)


def test_pipeline_list_returns_recent_jobs_newest_first(
    tmp_path: Path,
) -> None:
    fake_pipeline = tmp_path / 'fake_pipeline.py'
    fake_pipeline.write_text(
        'print("bootstrap done")\n', encoding='utf-8'
    )
    template = f'{sys.executable} {fake_pipeline}'
    gen = _run_pipeline_server(tmp_path, template)
    base_url = next(gen)
    try:
        first = _post_and_wait(base_url, {'command': 'bootstrap', 'agency': 'MinC'})
        second = _post_and_wait(base_url, {'command': 'bootstrap', 'agency': 'MTur'})
        listing = _get(f'{base_url}/api/pipeline')
        assert [j['status'] for j in listing['jobs']] == ['succeeded', 'succeeded']
        assert listing['jobs'][0]['command'].endswith('MTur')
        assert listing['jobs'][1]['command'].endswith('MinC')
        for job in listing['jobs']:
            assert 'started_at' in job and 'job_id' in job
        assert first['status'] == second['status'] == 'succeeded'
    finally:
        next(gen, None)


def test_pipeline_list_caps_retained_jobs(tmp_path: Path) -> None:
    fake_pipeline = tmp_path / 'fake_pipeline.py'
    fake_pipeline.write_text('print("done")\n', encoding='utf-8')
    template = f'{sys.executable} {fake_pipeline}'
    gen = _run_pipeline_server(tmp_path, template)
    base_url = next(gen)
    try:
        for _ in range(22):
            _post_and_wait(base_url, {'command': 'bootstrap', 'agency': 'MinC'})
        listing = _get(f'{base_url}/api/pipeline')
        assert len(listing['jobs']) == 20
    finally:
        next(gen, None)


def test_pipeline_non_run_command_has_no_warnings(
    tmp_path: Path,
) -> None:
    fake_pipeline = tmp_path / 'fake_pipeline.py'
    fake_pipeline.write_text(
        'print("bootstrap done, no json summary here")\n',
        encoding='utf-8',
    )
    template = f'{sys.executable} {fake_pipeline}'
    gen = _run_pipeline_server(tmp_path, template)
    base_url = next(gen)
    try:
        status = _post_and_wait(
            base_url,
            {'command': 'bootstrap', 'agency': 'MinC'},
        )
        assert status['status'] == 'succeeded'
        assert status['warnings'] == []
    finally:
        next(gen, None)
