from pathlib import Path

import pytest

from pyauditor.cli.main import cli_main
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


def _write_config_and_data(config_dir: Path, data_dir: Path, csv_body: str) -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    competencia_data_dir = data_dir / "2026" / "06"
    competencia_data_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "inms-test.yaml").write_text(CONFIG_YAML, encoding="utf-8")
    (competencia_data_dir / "data.csv").write_text(csv_body, encoding="utf-8")


def test_measure_reads_data_from_competencia_subfolder(tmp_path: Path) -> None:
    """`measure 2026-06 --data-dir input` reads CSVs from `input/2026/06/` —
    a stray file at the data-dir root must be ignored."""
    config_dir = tmp_path / "configs"
    data_dir = tmp_path / "input"
    output_dir = tmp_path / "roms"
    _write_config_and_data(
        config_dir,
        data_dir,
        "Nº Solicitacao;DataHoraFim;No prazo\n1;2026-06-01;S\n2;2026-06-02;N\n",
    )
    # Decoy at the data-dir root with the same name — shadows nothing, must be ignored.
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "data.csv").write_text(
        "Nº Solicitacao;DataHoraFim;No prazo\n1;2026-06-01;S\n", encoding="utf-8"
    )

    exit_code = run_measure("2026-06", config_dir, data_dir, output_dir)

    rom_path = output_dir / "2026-06" / "INMS-TEST.md"
    assert exit_code.status == "done"
    content = rom_path.read_text(encoding="utf-8")
    assert "- Numerador: 1.0\n- Denominador: 2.0" in content

    # A different competência reads its own folder from the same data-dir.
    (data_dir / "2026" / "05").mkdir(parents=True, exist_ok=True)
    (data_dir / "2026" / "05" / "data.csv").write_text(
        "Nº Solicitacao;DataHoraFim;No prazo\n1;2026-05-01;N\n2;2026-05-02;N\n",
        encoding="utf-8",
    )
    run_measure("2026-05", config_dir, data_dir, output_dir)
    rom_05 = (output_dir / "2026-05" / "INMS-TEST.md").read_text(encoding="utf-8")
    assert "- Denominador: 2.0" in rom_05


def test_measure_writes_one_rom_per_indicator_and_is_idempotent(tmp_path: Path) -> None:
    config_dir = tmp_path / "configs"
    data_dir = tmp_path / "input"
    output_dir = tmp_path / "roms"
    _write_config_and_data(
        config_dir,
        data_dir,
        "Nº Solicitacao;DataHoraFim;No prazo\n1;2026-06-01;S\n2;2026-06-02;N\n",
    )

    exit_code = run_measure("2026-06", config_dir, data_dir, output_dir)

    rom_path = output_dir / "2026-06" / "INMS-TEST.md"
    assert exit_code.status == "done"
    assert rom_path.exists()
    first_write = rom_path.read_text(encoding="utf-8")

    # Rerun with different data — the ROM must reflect the new run, not accumulate.
    _write_config_and_data(
        config_dir,
        data_dir,
        "Nº Solicitacao;DataHoraFim;No prazo\n1;2026-06-01;S\n",
    )
    run_measure("2026-06", config_dir, data_dir, output_dir)
    second_write = rom_path.read_text(encoding="utf-8")

    assert first_write != second_write
    assert "Numerador: 1" in second_write
    assert "Numerador: 1\n- Denominador: 2" not in second_write


def test_measure_exits_nonzero_on_hard_failure(tmp_path: Path) -> None:
    config_dir = tmp_path / "configs"
    data_dir = tmp_path / "input"
    output_dir = tmp_path / "roms"
    # Every row fails the not_null(DataHoraFim) check -> zero accepted rows.
    _write_config_and_data(
        config_dir,
        data_dir,
        "Nº Solicitacao;DataHoraFim;No prazo\n1;;S\n2;;N\n",
    )

    exit_code = run_measure("2026-06", config_dir, data_dir, output_dir)

    assert exit_code.status == "error"
    rom_path = output_dir / "2026-06" / "INMS-TEST.md"
    assert rom_path.exists()  # ROM still written so rejections are visible


def _write_per_orgao_config_and_data(
    tmp_path: Path, orgao: str, contract: str, csv_body: str
) -> None:
    config_dir = tmp_path / "configs" / orgao
    data_dir = tmp_path / "input" / orgao
    config_dir.mkdir(parents=True, exist_ok=True)
    month_dir = data_dir / "2026" / "06"
    month_dir.mkdir(parents=True, exist_ok=True)
    yaml = CONFIG_YAML
    if orgao != "MinC":
        yaml = yaml.replace("orgao: MinC", f"orgao: {orgao}")
        yaml = yaml.replace("Ministério da Cultura", contract)
    (config_dir / "inms-test.yaml").write_text(yaml, encoding="utf-8")
    (month_dir / "data.csv").write_text(csv_body, encoding="utf-8")


def test_measure_both_writes_per_orgao_and_combined_roms(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    config_dir = tmp_path / "configs"
    data_dir = tmp_path / "input"
    output_dir = tmp_path / "roms"
    _write_per_orgao_config_and_data(
        tmp_path,
        "MinC",
        "Ministério da Cultura",
        "Nº Solicitacao;DataHoraFim;No prazo\n1;2026-06-01;S\n2;2026-06-02;N\n",
    )
    _write_per_orgao_config_and_data(
        tmp_path,
        "MTur",
        "Ministério do Turismo",
        "Nº Solicitacao;DataHoraFim;No prazo\n1;2026-06-01;S\n",
    )

    code = cli_main(
        [
            "measure", "2026-06",
            "--orgao", "both",
            "--config-dir", str(config_dir),
            "--data-dir", str(data_dir),
            "--output-dir", str(output_dir),
        ]
    )

    assert code == 0
    per_minc = output_dir / "MinC" / "2026-06" / "INMS-TEST.md"
    per_mtur = output_dir / "MTur" / "2026-06" / "INMS-TEST.md"
    assert per_minc.exists()
    assert per_mtur.exists()

    combined = output_dir / "both" / "2026-06" / "INMS-TEST.md"
    assert combined.exists()
    combined_content = combined.read_text(encoding="utf-8")
    assert "# ROM — INMS TEST (Indicador sintético) — MinC e MTur" in combined_content
    assert combined_content.index("## MinC") < combined_content.index("## MTur")
    assert combined_content.count("### Resultado vs meta") == 2
    assert "- Órgão: MinC" in combined_content
    assert "- Órgão: MTur" in combined_content
