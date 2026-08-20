from pathlib import Path

import pytest

from pyauditor.excel.objetos import read_objetos

OBJETOS_CSV = """Item;Categoria;Valor Mensal do Contrato 40/2022
1;Central de Serviços;"R$ 148.205,54"
2;GT dos Projetos e Operações;"R$ 77.654,90"
3;Banco de Dados;"R$ 43.888,89"
4;"Aplicações, virtualização";"R$ 59.694,54"
5;Serviços Corporativos;"R$ 21.035,21"
6;Armazenamento e Backup;"R$ 16.145,94"
7;Redes;"R$ 31.382,28"
8;"Segurança da Informação";"R$ 34.143,44"
9;DevOps;"R$ 28.912,84"
TOTAL MENSAL;;"R$ 461.063,58"
TOTAL ANUAL;;"R$ 5.532.762,96"
"""


def _write(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8-sig")
    return path


def test_read_objetos_parses_items_and_totals(tmp_path: Path) -> None:
    path = _write(tmp_path / "objetos.csv", OBJETOS_CSV)

    objetos = read_objetos(path)

    assert len(objetos.itens) == 9
    assert objetos.itens[0] == 148205.54
    assert objetos.itens[8] == 28912.84
    assert objetos.total_mensal == 461063.58
    assert abs(objetos.total_mensal * 12 - objetos.total_anual) < 0.01
    assert objetos.warnings == ()


def test_warns_when_total_mensal_diverges_from_items(tmp_path: Path) -> None:
    body = OBJETOS_CSV.replace('"R$ 461.063,58"', '"R$ 400.000,00"')
    path = _write(tmp_path / "objetos.csv", body)

    objetos = read_objetos(path)

    assert objetos.total_mensal == 400000.0
    assert len(objetos.warnings) >= 1
    assert any("TOTAL MENSAL" in w and "diverge" in w for w in objetos.warnings)


def test_warns_when_total_anual_diverges_from_12x_mensal(tmp_path: Path) -> None:
    body = OBJETOS_CSV.replace('"R$ 5.532.762,96"', '"R$ 5.000.000,00"')
    path = _write(tmp_path / "objetos.csv", body)

    objetos = read_objetos(path)

    assert len(objetos.warnings) >= 1
    assert any("diverge de 'TOTAL MENSAL' × 12" in w for w in objetos.warnings)


def test_rejects_missing_total_mensal(tmp_path: Path) -> None:
    body = OBJETOS_CSV.replace('\nTOTAL MENSAL;;"R$ 461.063,58"', "")
    path = _write(tmp_path / "objetos.csv", body)

    with pytest.raises(ValueError, match="TOTAL MENSAL"):
        read_objetos(path)


def test_rejects_missing_total_anual(tmp_path: Path) -> None:
    body = OBJETOS_CSV.replace('\nTOTAL ANUAL;;"R$ 5.532.762,96"', "")
    path = _write(tmp_path / "objetos.csv", body)

    with pytest.raises(ValueError, match="TOTAL ANUAL"):
        read_objetos(path)


def test_rejects_non_numeric_item_index(tmp_path: Path) -> None:
    body = OBJETOS_CSV.replace("\n1;", "\nX;", 1)
    path = _write(tmp_path / "objetos.csv", body)

    with pytest.raises(ValueError, match="sem item numérico"):
        read_objetos(path)


def test_rejects_wrong_header(tmp_path: Path) -> None:
    path = _write(tmp_path / "objetos.csv", "a;b;c\n1;2;3\n")

    with pytest.raises(ValueError, match="cabeçalho esperado"):
        read_objetos(path)