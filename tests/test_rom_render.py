"""Peças novas do template de ROM de .scratch/melhoria_rom/map.md + spec
competencia-cli-equipe §5: Identificação (provenance), Competência/Período
derivados dos kwargs da CLI, Responsáveis via capa_fields (equipe.csv) e a
"Ressalva interpretativa" condicional (3 leituras da penalidade linear)."""

import sys
from datetime import date
from io import StringIO
from pathlib import Path

import pytest

from pyauditor.engine.pipeline import load_config, measure
from pyauditor.logging import setup_logging
from pyauditor.periodo import PeriodoAfericao
from pyauditor.rom.render import render_combined_rom, render_rom

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


def test_competencia_periodo_kwargs_e_capa_so_responsaveis(tmp_path: Path) -> None:
    """§5 — Competência/Período vêm dos kwargs da CLI; `capa_fields` alimenta
    só a seção Responsáveis (equipe.csv)."""
    config_path = _write_ratio_fixture(tmp_path, resultado=100.0)
    config = load_config(config_path)
    result = measure(config, data_dir=tmp_path, config_path=config_path)
    capa_fields: dict[str, object] = {
        "Fiscal técnico": "Fulano de Tal",
        "Fiscal requisitante": "Beltrano",
        "Fiscal administrativo": "Ciclana",
        "Gestor do contrato": "Sicrano",
    }
    periodo = PeriodoAfericao(date(2026, 6, 1), date(2026, 6, 30))

    rom = render_rom(result, capa_fields=capa_fields, competencia="2026-06", periodo=periodo)

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

    rom = render_rom(result)  # no capa_fields, no periodo — chamador legado

    assert "- Competência: [a preencher]" in rom
    assert "- Fiscal técnico: [a preencher]" in rom
    # sem filtro rodado, a linha de descarte não existe (nada de zero enganoso)
    assert "Fora do período descartadas" not in rom


def test_measure_emite_warn_de_janela_vazia_e_info_descarte(tmp_path: Path) -> None:
    """§3 — measure emite o WARN verbatim para o dataset whole_indicator que
    processa e INFO estruturado quando há descarte; contagens viajam no
    resultado."""
    yaml_com_periodo = """\
indicator:
  id: INMS-JANELA
  contractual_id: "INMS JANELA"
  name: Janela

scope:
  contract: "40/2022 - Ministério da Cultura"
  orgao: MinC

source:
  csv: data.csv
  delimiter: ","
  encoding: utf-8
  period_column: "DataHoraFim"

quality_gates:
  checks: []

calculation:
  shape: ratio
  aggregation: count_distinct
  numerator_filter:
    column: "Atendido"
    equals: "S"

target:
  operator: ">="
  value: 98.0

penalty:
  base_points: 50
  step_points: 100
  step_size_pct: 4.0
"""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml_com_periodo, encoding="utf-8")
    (tmp_path / "data.csv").write_text(
        "Nº Solicitação,DataHoraFim,Atendido\n1,20/05/2026 10:00,S\n", encoding="utf-8"
    )
    config = load_config(config_path)
    periodo = PeriodoAfericao(date(2026, 6, 1), date(2026, 6, 30))
    buf = StringIO()
    setup_logging(sink=buf, level="INFO")

    try:
        result = measure(config, data_dir=tmp_path, config_path=config_path, periodo=periodo)
    finally:
        setup_logging(sink=sys.stderr, level="INFO")

    logs = buf.getvalue()
    assert (
        "nenhuma linha no período 01/06/2026–30/06/2026 "
        "— o arquivo corresponde à competência?" in logs
    )
    assert "1 linha(s) fora do período descartada(s)" in logs
    assert result.dropped_out_of_period == 1


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

    assert "são derivados do argumento --competência da CLI" in rom
    assert "Responsáveis refletem o estado da capa no momento em que este ROM foi gerado" in rom


def test_render_combined_rom_stacks_both_orgaos(tmp_path: Path) -> None:
    """The `both` markdown nests each orgão's full ROM body under its own
    `## <órgão>` heading (sections drop one level to `###`)."""
    minc_path = _write_orgao_fixture(tmp_path, "MinC", resultado=91.0)
    mtur_path = _write_orgao_fixture(tmp_path, "MTur", resultado=100.0)
    result_minc = measure(load_config(minc_path), data_dir=tmp_path, config_path=minc_path)
    result_mtur = measure(load_config(mtur_path), data_dir=tmp_path, config_path=mtur_path)

    rom = render_combined_rom(result_minc, result_mtur)

    assert rom.startswith("# ROM — INMS TEST (Indicador sintético) — MinC e MTur\n")
    assert "## MinC" in rom and "## MTur" in rom
    assert "### Identificação" in rom
    assert "### Resultado vs meta" in rom
    # footer once per orgão (texto aprovado da spec §5)
    assert rom.count("são derivados do argumento --competência da CLI") == 2
    # Per-orgão sections keep their own scope, MinC first.
    assert rom.index("## MinC") < rom.index("## MTur")


def test_linhas_fora_do_periodo_aparece_somente_com_filtro(tmp_path: Path) -> None:
    """§5 — a linha `- Fora do período descartadas: N` só existe quando o
    filtro rodou (a ausência é coberta por
    `test_missing_capa_fields_render_placeholder`, que renderiza sem filtro)."""
    yaml = _RATIO_YAML.replace('delimiter: ","', 'delimiter: ","\n  period_column: "Data"')
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml, encoding="utf-8")
    # 2 linhas brutas: a fora da janela é descartada -> sobra exatamente 1
    # linha, exigência do `aggregation: precomputed`.
    (tmp_path / "data.csv").write_text(
        "Descrição,Resultado,Data\nX,100.0,2026-06\nY,50.0,2026-05\n", encoding="utf-8"
    )
    config = load_config(config_path)
    periodo = PeriodoAfericao(date(2026, 6, 1), date(2026, 6, 30))

    result = measure(config, data_dir=tmp_path, config_path=config_path, periodo=periodo)
    rom = render_rom(result)

    assert result.dropped_out_of_period == 1
    assert "- Fora do período descartadas: 1" in rom


def _write_orgao_fixture(tmp_path: Path, orgao: str, *, resultado: float) -> Path:
    yaml = _RATIO_YAML
    if orgao != "MinC":
        yaml = yaml.replace("orgao: MinC", f"orgao: {orgao}")
        yaml = yaml.replace("Ministério da Cultura", "Ministério do Turismo")
    config_path = tmp_path / f"{orgao}.yaml"
    config_path.write_text(yaml, encoding="utf-8")
    (tmp_path / "data.csv").write_text(f"Descrição,Resultado\nX,{resultado}\n", encoding="utf-8")
    return config_path
