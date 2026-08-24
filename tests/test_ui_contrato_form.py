from __future__ import annotations

from pathlib import Path

import pytest

from ui.contrato_form import read_contrato, save_contrato


def make_workspace(tmp_path: Path) -> Path:
    (tmp_path / 'configs' / 'dados_contratuais.yaml').parent.mkdir(
        parents=True, exist_ok=True
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


def test_read_contrato_returns_all_three_sections(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)

    doc = read_contrato(workspace)

    assert doc['dados_contratuais']['config']['Fator-K máximo'] == '2,35'
    assert doc['ajuste_inms']['config']['formula'] == 'A'
    assert doc['desconto_regulatorio']['config']['descricao'] == 'D'
    assert doc['desconto_regulatorio']['path'] == (
        'configs/desconto_regulatório.yaml'
    )


def test_save_contrato_round_trips(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    doc = read_contrato(workspace)
    doc['dados_contratuais']['config']['Fator-K máximo'] = '3,00'
    doc['ajuste_inms']['config']['formula'] = 'A2'

    save_contrato(workspace, doc)

    reloaded = read_contrato(workspace)
    assert reloaded['dados_contratuais']['config']['Fator-K máximo'] == ('3,00')
    assert reloaded['ajuste_inms']['config']['formula'] == 'A2'
    assert reloaded['desconto_regulatorio']['config']['formula'] == 'C'


def test_save_contrato_rejects_non_string_value(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    doc = read_contrato(workspace)
    doc['ajuste_inms']['config']['formula'] = 123

    with pytest.raises(ValueError):
        save_contrato(workspace, doc)


def test_save_contrato_rejects_path_escaping_workspace(
    tmp_path: Path,
) -> None:
    workspace = make_workspace(tmp_path)
    doc = read_contrato(workspace)
    doc['ajuste_inms']['path'] = '../../outside/ajuste_inms.yaml'

    with pytest.raises(ValueError):
        save_contrato(workspace, doc)
