from __future__ import annotations

from pathlib import Path

import pytest

from ui.datasets_form import read_datasets, save_datasets

_DATASETS = """\
datasets:
  telefonemas:
    file: inms-11.csv
    delimiter: ";"
    encoding: utf-8-sig
"""


def make_workspace(tmp_path: Path) -> Path:
    shared = tmp_path / 'configs' / '_shared'
    shared.mkdir(parents=True)
    (shared / 'datasets.yaml').write_text(_DATASETS, encoding='utf-8')
    return tmp_path


def test_read_datasets_returns_alias_map(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    doc = read_datasets(workspace)

    assert doc['path'] == 'configs/_shared/datasets.yaml'
    assert doc['datasets']['telefonemas']['file'] == 'inms-11.csv'


def test_read_datasets_prefers_shared_over_other_copies(
    tmp_path: Path,
) -> None:
    workspace = make_workspace(tmp_path)
    org_dir = workspace / 'configs' / 'MinC'
    org_dir.mkdir(parents=True)
    (org_dir / 'datasets.yaml').write_text(
        'datasets:\n  outros:\n    file: x.csv\n', encoding='utf-8'
    )

    doc = read_datasets(workspace)

    assert doc['path'] == 'configs/_shared/datasets.yaml'


def test_save_datasets_round_trips(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    doc = read_datasets(workspace)
    doc['datasets']['telefonemas']['delimiter'] = ','
    doc['datasets']['novo'] = {
        'file': 'novo.csv',
        'delimiter': ';',
        'encoding': 'utf-8-sig',
    }

    save_datasets(workspace, doc)

    reloaded = read_datasets(workspace)
    assert reloaded['datasets']['telefonemas']['delimiter'] == ','
    assert reloaded['datasets']['novo']['file'] == 'novo.csv'


def test_save_datasets_rejects_invalid_entry(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    doc = read_datasets(workspace)
    doc['datasets']['telefonemas'] = {'delimiter': ';'}

    with pytest.raises(ValueError):
        save_datasets(workspace, doc)


def test_save_datasets_rejects_path_escaping_workspace(
    tmp_path: Path,
) -> None:
    workspace = make_workspace(tmp_path)
    doc = read_datasets(workspace)
    doc['path'] = '../../outside/datasets.yaml'

    with pytest.raises(ValueError):
        save_datasets(workspace, doc)
