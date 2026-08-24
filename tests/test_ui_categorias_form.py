from __future__ import annotations

from pathlib import Path

import pytest

from ui.categorias_form import read_categoria, save_categoria

_CATEGORIAS = """\
categorias:
  ATENDIMENTO_N1:
    label: "Atendimento Remoto"
    inms:
      "1.1": {mode: grupo_executor, in_values: ["A"]}
      "1.7": {mode: whole_indicator}
"""


def make_workspace(tmp_path: Path) -> Path:
    for orgao in ('MinC', 'MTur'):
        org_dir = tmp_path / 'configs' / orgao
        org_dir.mkdir(parents=True)
        (org_dir / 'categorias.yaml').write_text(_CATEGORIAS, encoding='utf-8')
    return tmp_path


def test_read_categoria_returns_orgao_doc(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    doc = read_categoria(workspace, 'MinC')

    assert doc['orgao'] == 'MinC'
    assert doc['path'] == 'configs/MinC/categorias.yaml'
    assert doc['config']['categorias']['ATENDIMENTO_N1']['label'] == (
        'Atendimento Remoto'
    )


def test_read_categoria_unknown_orgao_raises(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    with pytest.raises(ValueError):
        read_categoria(workspace, 'Nope')


def test_save_categoria_round_trips(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    doc = read_categoria(workspace, 'MinC')
    doc['config']['categorias']['ATENDIMENTO_N1']['inms']['1.1'][
        'in_values'
    ] = ['B']

    save_categoria(workspace, doc)

    reloaded = read_categoria(workspace, 'MinC')
    assert reloaded['config']['categorias']['ATENDIMENTO_N1']['inms']['1.1'][
        'in_values'
    ] == ['B']


def test_save_categoria_rejects_invalid_config(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    doc = read_categoria(workspace, 'MinC')
    doc['config']['categorias']['ATENDIMENTO_N1']['inms']['1.1'] = {
        'mode': 'grupo_executor',
        'in_values': ['A'],
        'catch_all_contains': 'both set',
    }

    with pytest.raises(ValueError):
        save_categoria(workspace, doc)


def test_save_categoria_rejects_path_escaping_workspace(
    tmp_path: Path,
) -> None:
    workspace = make_workspace(tmp_path)
    doc = read_categoria(workspace, 'MinC')
    doc['path'] = '../../outside/categorias.yaml'

    with pytest.raises(ValueError):
        save_categoria(workspace, doc)
