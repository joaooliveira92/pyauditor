from pathlib import Path

import pytest

from pyauditor.excel.capa import (
    COMMON_FIELD_LABELS,
    ORGAO_FIELD_LABELS,
    read_capa_csv_fields,
    bootstrap_capa_csv,
)
from pyauditor.excel.objetos import parse_brl_value


def test_bootstrap_creates_capa_with_expected_common_fields(tmp_path: Path) -> None:
    capa_path = tmp_path / "capa.csv"

    created = bootstrap_capa_csv(capa_path, COMMON_FIELD_LABELS)

    assert created is True
    assert capa_path.exists()
    fields = read_capa_csv_fields(capa_path)
    assert set(fields) == set(COMMON_FIELD_LABELS)
    assert all(v == "" for v in fields.values())


def test_bootstrap_defaults_only_situacao_on_orgao_capa(tmp_path: Path) -> None:
    capa_path = tmp_path / "capa_MinC.csv"
    bootstrap_capa_csv(capa_path, ORGAO_FIELD_LABELS)

    fields = read_capa_csv_fields(capa_path)
    assert fields["Situação geral da aferição"] == "Em preenchimento"
    assert fields["Fiscal técnico"] == ""


def test_bootstrap_is_idempotent_never_overwrites(tmp_path: Path) -> None:
    capa_path = tmp_path / "capa.csv"
    bootstrap_capa_csv(capa_path, COMMON_FIELD_LABELS)
    mtime_before = capa_path.stat().st_mtime_ns

    created_again = bootstrap_capa_csv(capa_path, COMMON_FIELD_LABELS)

    assert created_again is False
    assert capa_path.stat().st_mtime_ns == mtime_before


def test_bootstrap_creates_parent_directories(tmp_path: Path) -> None:
    capa_path = tmp_path / "nested" / "dir" / "capa.csv"

    created = bootstrap_capa_csv(capa_path, COMMON_FIELD_LABELS)

    assert created is True
    assert capa_path.exists()


def test_read_capa_csv_roundtrips_fiscal_filled_value(tmp_path: Path) -> None:
    capa_path = tmp_path / "capa_MinC.csv"
    bootstrap_capa_csv(capa_path, ORGAO_FIELD_LABELS)

    capa_path.write_text(
        "Capa e controle do contrato;\n;\nCampo;Valor\n"
        "Fiscal técnico;João Antônio\n"
        "Situação geral da aferição;Em preenchimento\n",
        encoding="utf-8-sig",
    )

    fields = read_capa_csv_fields(capa_path)
    assert fields["Fiscal técnico"] == "João Antônio"


def test_read_capa_csv_fields_rejects_duplicate_label(tmp_path: Path) -> None:
    capa_path = tmp_path / "capa.csv"
    capa_path.write_text(
        "Capa e controle do contrato;\n;\nCampo;Valor\n"
        "Número do contrato;40/2022\n"
        "Número do contrato;OUTRO\n",
        encoding="utf-8-sig",
    )

    with pytest.raises(ValueError, match="duplicado"):
        read_capa_csv_fields(capa_path)


def test_parse_brl_value_accepts_ptbr_and_machine_shapes() -> None:
    assert parse_brl_value("R$ 148.205,54") == 148205.54
    assert parse_brl_value("461.063,58") == 461063.58
    assert parse_brl_value("148205.54") == 148205.54
    assert parse_brl_value("0") == 0.0


def test_parse_brl_value_rejects_garbage() -> None:
    with pytest.raises(ValueError, match="inválido"):
        parse_brl_value("abc")