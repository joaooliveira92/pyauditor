from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from pyauditor.cli.measure import run_measure

CONFIG_YAML = """\
indicator:
  id: INMS-TEST
  contractual_id: "INMS TEST"
  name: Indicador sintético

scope:
  contract: "40/2022 - Ministério da Cultura"
  orgao: MinC

source:
  csv: data.csv
  delimiter: ";"
  encoding: utf-8
  period_column: "DataHoraFim"

quality_gates:
  checks:
    - type: not_null
      column: "DataHoraFim"

calculation:
  shape: ratio
  aggregation: count_distinct
  numerator_filter:
    column: "No prazo"
    equals: "S"

target:
  operator: ">="
  value: 98.0

penalty:
  base_points: 100
  step_points: 10
  step_size_pct: 1.0
"""

_CSV_HEADER = "Nº Solicitacao;DataHoraFim;No prazo"
_CSV_OK = f"{_CSV_HEADER}\n1;2026-06-01;S\n2;2026-06-02;N\n"
_CSV_HARD = f"{_CSV_HEADER}\n1;;\n2;;\n"


def _write_data(data_dir: Path, csv_name: str, body: str) -> Path:
    competencia_data_dir = data_dir / "2026" / "06"
    competencia_data_dir.mkdir(parents=True, exist_ok=True)
    path = competencia_data_dir / csv_name
    path.write_text(body, encoding="utf-8")
    return path


def _write_config(
    config_dir: Path,
    *,
    yaml_name: str,
    indicator_id: str = "INMS-TEST",
    contractual_id: str = "INMS TEST",
    csv: str = "data.csv",
) -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    yaml_body = CONFIG_YAML
    if csv != "data.csv":
        yaml_body = yaml_body.replace("csv: data.csv", f"csv: {csv}")
    yaml_body = yaml_body.replace("INMS-TEST", indicator_id)
    yaml_body = yaml_body.replace("INMS TEST", contractual_id)
    (config_dir / yaml_name).write_text(yaml_body, encoding="utf-8")


def _fixture(tmp_path: Path, csv_body: str = _CSV_OK) -> tuple[Path, Path, Path]:
    config_dir = tmp_path / "configs"
    data_dir = tmp_path / "input"
    out_dir = tmp_path / "roms"
    _write_config(config_dir, yaml_name="inms-test.yaml")
    _write_data(data_dir, "data.csv", csv_body)
    return config_dir, data_dir, out_dir


def test_happy_path(tmp_path: Path) -> None:
    config_dir, data_dir, out_dir = _fixture(tmp_path)

    code = run_measure("2026-06", config_dir, data_dir, out_dir)

    assert code.status == "done"
    assert (out_dir / "2026-06" / "INMS-TEST.md").exists()
    assert (out_dir / "2026-06" / "INMS-TEST.json").exists()


def test_no_configs_returns_1(tmp_path: Path) -> None:
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    assert run_measure("2026-06", config_dir, tmp_path, tmp_path).status == "error"


def test_invalid_competencia_rejected(tmp_path: Path) -> None:
    assert run_measure("2026/06", tmp_path, tmp_path, tmp_path).status == "error"
    assert run_measure("../../etc", tmp_path, tmp_path, tmp_path).status == "error"
    assert run_measure("2026-13-extra", tmp_path, tmp_path, tmp_path).status == "error"


def test_sanitize_id_prevents_traversal(tmp_path: Path) -> None:
    config_dir = tmp_path / "configs"
    data_dir = tmp_path / "input"
    out_dir = tmp_path / "roms"
    _write_config(
        config_dir,
        yaml_name="inms-evil.yaml",
        indicator_id="../../evil",
        contractual_id="C-EVIL",
    )
    _write_data(data_dir, "data.csv", _CSV_OK)

    code = run_measure("2026-06", config_dir, data_dir, out_dir)

    assert code.status == "done"
    assert (out_dir / "2026-06" / "evil.md").exists()
    assert not (tmp_path / "evil.md").exists()


def test_mkdir_oserror_returns_1(tmp_path: Path) -> None:
    config_dir, data_dir, _ = _fixture(tmp_path)
    with patch.object(Path, "mkdir", side_effect=OSError("ro")):
        assert run_measure("2026-06", config_dir, data_dir, tmp_path).status == "error"


def test_write_oserror_marks_hard_failure(tmp_path: Path) -> None:
    config_dir, data_dir, out_dir = _fixture(tmp_path)
    with patch.object(Path, "write_text", side_effect=OSError("disk full")):
        code = run_measure("2026-06", config_dir, data_dir, out_dir)
    assert code.status == "error"
    failing = next((i for i in code.indicators if i.hard_failure), None)
    assert failing is not None
    assert failing.error is not None and "falha ao escrever" in failing.error


def test_measure_exception_continues(tmp_path: Path) -> None:
    """Um dataset ausente (`not_activated`) não aborta a passada — os demais
    indicadores medem normalmente na mesma execução."""
    config_dir, data_dir, out_dir = _fixture(tmp_path)
    # Segundo indicador apontando para CSV que não existe na competência.
    _write_config(
        config_dir,
        yaml_name="inms-missing.yaml",
        indicator_id="INMS-MISSING",
        contractual_id="INMS OUTRO",
        csv="missing.csv",
    )

    code = run_measure("2026-06", config_dir, data_dir, out_dir)

    assert len(code.indicators) == 2
    missing = next(i for i in code.indicators if i.rom_path.name == "INMS-MISSING.md")
    assert missing.hard_failure is False
    assert missing.not_activated is True
    ok = next(i for i in code.indicators if i.rom_path.name == "INMS-TEST.md")
    assert ok.hard_failure is False
    assert ok.rom_path.exists()


def test_missing_equipe_warns_but_does_not_fail(tmp_path: Path) -> None:
    config_dir, data_dir, out_dir = _fixture(tmp_path)
    missing_equipe = tmp_path / "equipe.csv"

    code = run_measure("2026-06", config_dir, data_dir, out_dir, equipe_path=missing_equipe)

    assert code.status == "done"
    assert any("equipe não encontrada" in w for w in code.warnings)


def test_equipe_missing_fields_warn_once_per_run(tmp_path: Path) -> None:
    config_dir, data_dir, out_dir = _fixture(tmp_path)
    equipe_path = tmp_path / "equipe.csv"
    equipe_path.write_text(
        "FUNÇÃO,NOME,SIAPE\nFiscal técnico,Fulano de Tal,1234567\n",
        encoding="utf-8-sig",
    )

    code = run_measure("2026-06", config_dir, data_dir, out_dir, equipe_path=equipe_path)

    resumo = [w for w in code.warnings if "sem preencher" in w]
    assert len(resumo) == 1  # o resumo agregado é uma vez por execução
    assert "Fiscal requisitante" in resumo[0]
    assert "Fiscal técnico" not in resumo[0]  # esse foi preenchido


def test_equipe_fields_reach_render_rom_and_malformed_degrades(tmp_path: Path) -> None:
    config_dir, data_dir, out_dir = _fixture(tmp_path)
    equipe_path = tmp_path / "equipe.csv"
    equipe_path.write_text(
        "FUNÇÃO,NOME,SIAPE\nGestor do Contrato,Beltrano,7654321\n",
        encoding="utf-8-sig",
    )

    code = run_measure("2026-06", config_dir, data_dir, out_dir, equipe_path=equipe_path)

    assert code.status == "done"
    rom_text = (out_dir / "2026-06" / "INMS-TEST.md").read_text(encoding="utf-8")
    assert "Gestor do contrato: Beltrano (7654321)" in rom_text

    # Malformado é dado incompleto, não falha — Responsáveis voltam ao placeholder.
    equipe_path.write_text("cabecalho,errado\n", encoding="utf-8-sig")
    code = run_measure("2026-06", config_dir, data_dir, out_dir, equipe_path=equipe_path)
    assert code.status == "done"
    rom_text = (out_dir / "2026-06" / "INMS-TEST.md").read_text(encoding="utf-8")
    assert "[a preencher]" in rom_text
    assert any("falha ao ler" in w for w in code.warnings)