"""New ROM template pieces from .scratch/melhoria_rom/map.md: Identificação
(provenance), capa-sourced Competência/Período/Responsáveis, and the
conditional "Ressalva interpretativa" (3 readings of the linear penalty)."""

from pathlib import Path

import pytest

from pyauditor.engine.pipeline import load_config, measure
from pyauditor.rom.render import render_rom

_RATIO_YAML = """
indicator:
  id: INMS-TEST-RESSALVA
  contractual_id: "INMS TEST"
  name: Indicador sintético

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
  aggregation: precomputed
  precomputed_result_column: "Resultado"

target:
  operator: ">="
  value: 100.0

penalty:
  base_points: 50
  step_points: 100
  step_size_pct: 4.0
"""


def _write_ratio_fixture(tmp_path: Path, *, resultado: float) -> Path:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(_RATIO_YAML, encoding="utf-8")
    (tmp_path / "data.csv").write_text(f"Descrição,Resultado\nX,{resultado}\n", encoding="utf-8")
    return config_path


def test_identificacao_section_has_provenance(tmp_path: Path) -> None:
    config_path = _write_ratio_fixture(tmp_path, resultado=100.0)
    config = load_config(config_path)
    result = measure(config, data_dir=tmp_path, config_path=config_path)

    rom = render_rom(result)

    assert "## Identificação" in rom
    assert "- Contrato: 40/2022 - Ministério da Cultura" in rom
    assert "- Órgão: MinC" in rom
    assert f"- Versão da configuração: {result.provenance.config_hash}" in rom
    assert f"(SHA-256: {result.provenance.csv_hash}" in rom
    assert "delimitador `,`" in rom
    assert "codificação utf-8" in rom


def test_identificacao_without_config_path_shows_unavailable(tmp_path: Path) -> None:
    config_path = _write_ratio_fixture(tmp_path, resultado=100.0)
    config = load_config(config_path)
    result = measure(config, data_dir=tmp_path)  # no config_path passed

    rom = render_rom(result)

    assert "- Versão da configuração: [indisponível]" in rom


def test_capa_fields_fill_identificacao_and_responsaveis(tmp_path: Path) -> None:
    config_path = _write_ratio_fixture(tmp_path, resultado=100.0)
    config = load_config(config_path)
    result = measure(config, data_dir=tmp_path, config_path=config_path)
    capa_fields: dict[str, object] = {
        "Competência": "2026-06",
        "Período inicial da aferição": "01/06/2026",
        "Período final da aferição": "30/06/2026",
        "Fiscal técnico": "Fulano de Tal",
        "Fiscal requisitante": "Beltrano",
        "Fiscal administrativo": "Ciclana",
        "Gestor do contrato": "Sicrano",
    }

    rom = render_rom(result, capa_fields=capa_fields)

    assert "- Competência: 2026-06" in rom
    assert "- Período da aferição: 01/06/2026 a 30/06/2026" in rom
    assert "## Responsáveis" in rom
    assert "- Fiscal técnico: Fulano de Tal" in rom
    assert "- Fiscal requisitante: Beltrano" in rom
    assert "- Fiscal administrativo: Ciclana" in rom
    assert "- Gestor do contrato: Sicrano" in rom


def test_missing_capa_fields_render_placeholder(tmp_path: Path) -> None:
    config_path = _write_ratio_fixture(tmp_path, resultado=100.0)
    config = load_config(config_path)
    result = measure(config, data_dir=tmp_path, config_path=config_path)

    rom = render_rom(result)  # no capa_fields at all

    assert "- Competência: [a preencher]" in rom
    assert "- Fiscal técnico: [a preencher]" in rom


def test_pontuacao_apurada_label_replaces_penalidade(tmp_path: Path) -> None:
    config_path = _write_ratio_fixture(tmp_path, resultado=91.0)
    config = load_config(config_path)
    result = measure(config, data_dir=tmp_path, config_path=config_path)

    rom = render_rom(result)

    assert "- Pontuação apurada:" in rom
    assert "- Penalidade:" not in rom


def test_ressalva_interpretativa_shown_with_correct_readings(tmp_path: Path) -> None:
    # shortfall 9.0 p.p. / step_size 4.0 -> 2.25 degraus (fractional on purpose)
    config_path = _write_ratio_fixture(tmp_path, resultado=91.0)
    config = load_config(config_path)
    result = measure(config, data_dir=tmp_path, config_path=config_path)

    rom = render_rom(result)

    assert result.calculation.penalty_points == pytest.approx(275.0)  # 50 + 2.25*100
    assert "## Ressalva interpretativa" in rom
    assert "Linear contínua (adotada)" in rom and "| 275.00 |" in rom
    assert "Degraus completos" in rom and "| 250.00 |" in rom
    assert "Qualquer fração inicia novo degrau" in rom and "| 350.00 |" in rom


def test_ressalva_interpretativa_omitted_when_conforms(tmp_path: Path) -> None:
    config_path = _write_ratio_fixture(tmp_path, resultado=100.0)
    config = load_config(config_path)
    result = measure(config, data_dir=tmp_path, config_path=config_path)

    rom = render_rom(result)

    assert result.calculation.conforms is True
    assert "## Ressalva interpretativa" not in rom


def test_ressalva_interpretativa_omitted_when_shape_has_no_penalty(tmp_path: Path) -> None:
    """`count_difference` never sets `config.penalty` — no linear-vs-degraus
    ambiguity to disclose even though it does have a `penalty_points` > 0."""
    config_yaml = """
indicator:
  id: INMS-TEST-CD
  contractual_id: "INMS TEST CD"
  name: Indicador sintético count_difference

scope:
  contract: "40/2022 - Ministério da Cultura"
  orgao: MinC

source:
  csv: data.csv
  delimiter: ";"
  encoding: utf-8

quality_gates:
  checks: []

calculation:
  shape: count_difference
  implemented_filter:
    column: "Status"
    equals: "Implantado"
  penalty_per_unit: 100

target:
  operator: ">="
  value: 100.0
"""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(config_yaml, encoding="utf-8")
    (tmp_path / "data.csv").write_text(
        "Item;Status\nA;Implantado\nB;Recomendado\nC;Recomendado\n", encoding="utf-8"
    )
    config = load_config(config_path)
    result = measure(config, data_dir=tmp_path, config_path=config_path)

    rom = render_rom(result)

    assert result.calculation.penalty_points > 0
    assert config.penalty is None
    assert "## Ressalva interpretativa" not in rom


def test_linhas_aprovadas_replaces_populacao_label(tmp_path: Path) -> None:
    config_path = _write_ratio_fixture(tmp_path, resultado=100.0)
    config = load_config(config_path)
    result = measure(config, data_dir=tmp_path, config_path=config_path)

    rom = render_rom(result)

    assert "## Linhas aprovadas pelo quality gate" in rom
    assert "## População" not in rom
    assert "não equivale à população contratual completa" in rom


def test_footer_note_present(tmp_path: Path) -> None:
    config_path = _write_ratio_fixture(tmp_path, resultado=100.0)
    config = load_config(config_path)
    result = measure(config, data_dir=tmp_path, config_path=config_path)

    rom = render_rom(result)

    assert "refletem o estado da capa no momento" in rom
