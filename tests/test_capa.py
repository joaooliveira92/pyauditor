from pathlib import Path

import pytest

from pyauditor.excel.capa import (
    COMMON_FIELD_LABELS,
    ORGAO_FIELD_LABELS,
    read_capa_csv_fields,
    bootstrap_capa_csv,
    validate_periodo_competencia,
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


def test_validate_periodo_competencia_empty_fields_no_warning() -> None:
    # Ticket 10: campo vazio não é assunto deste validador (ticket 02 cuida
    # disso via missing_publication_fields).
    assert validate_periodo_competencia({}, "2026-06") == ()


def test_validate_periodo_competencia_all_consistent_no_warning() -> None:
    campos: dict[str, object] = {
        "Competência": "2026-06",
        "Período inicial da aferição": "01/06/2026",
        "Período final da aferição": "30/06/2026",
    }

    assert validate_periodo_competencia(campos, "2026-06") == ()


def test_validate_periodo_competencia_warns_on_competencia_divergente() -> None:
    campos: dict[str, object] = {"Competência": "2026-05"}

    warnings = validate_periodo_competencia(campos, "2026-06")

    assert len(warnings) == 1
    assert "2026-05" in warnings[0]
    assert "2026-06" in warnings[0]


def test_validate_periodo_competencia_warns_on_periodo_fora_do_mes() -> None:
    campos: dict[str, object] = {
        "Período inicial da aferição": "28/05/2026",
        "Período final da aferição": "30/06/2026",
    }

    warnings = validate_periodo_competencia(campos, "2026-06")

    assert len(warnings) == 1
    assert "Período inicial da aferição" in warnings[0]
    assert "fora dos limites" in warnings[0]


def test_validate_periodo_competencia_warns_on_inicio_posterior_ao_fim() -> None:
    campos: dict[str, object] = {
        "Período inicial da aferição": "20/06/2026",
        "Período final da aferição": "10/06/2026",
    }

    warnings = validate_periodo_competencia(campos, "2026-06")

    assert len(warnings) == 1
    assert "posterior ao" in warnings[0]


def test_validate_periodo_competencia_warns_on_formato_invalido() -> None:
    campos: dict[str, object] = {"Período inicial da aferição": "junho/2026"}

    warnings = validate_periodo_competencia(campos, "2026-06")

    assert len(warnings) == 1
    assert "DD/MM/AAAA" in warnings[0]