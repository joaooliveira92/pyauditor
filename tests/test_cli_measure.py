from pathlib import Path
from unittest.mock import patch

import pytest

from pyauditor.cli.main import cli_main
from pyauditor.cli.measure import run_measure
from pyauditor.cli.split import run_split

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


def test_measure_os_error_writing_rom_has_actionable_hint(tmp_path: Path) -> None:
    # Ticket 11: falha ao gravar o ROM (permissão/lock) ganha dica acionável.
    config_dir = tmp_path / "configs"
    data_dir = tmp_path / "input"
    output_dir = tmp_path / "roms"
    _write_config_and_data(
        config_dir, data_dir,
        "Nº Solicitacao;DataHoraFim;No prazo\n1;2026-06-01;S\n2;2026-06-02;N\n",
    )

    with patch.object(Path, "write_text", side_effect=PermissionError("Permission denied")):
        exit_code = run_measure("2026-06", config_dir, data_dir, output_dir)

    assert exit_code.status == "error"
    failing = next(i for i in exit_code.indicators if i.hard_failure)
    assert failing.error is not None
    assert "aberto em outro programa" in failing.error


def test_measure_missing_dataset_is_not_activated_not_a_failure(tmp_path: Path) -> None:
    """Spec §14.1: um CSV ausente na competência não é falha de medição — o
    elemento contratual não foi demandado/ativado no período. `measure` deve
    completar com sucesso, emitir o WARNING e marcar o indicador como
    `not_activated`, sem escrever ROM/JSON para ele."""
    config_dir = tmp_path / "configs"
    data_dir = tmp_path / "input"
    output_dir = tmp_path / "roms"
    config_dir.mkdir(parents=True)
    (data_dir / "2026" / "06").mkdir(parents=True)
    (config_dir / "inms-test.yaml").write_text(
        CONFIG_YAML.replace("csv: data.csv", "csv: missing.csv"), encoding="utf-8"
    )

    exit_code = run_measure("2026-06", config_dir, data_dir, output_dir)

    assert exit_code.status == "done"
    outcome = exit_code.indicators[0]
    assert outcome.not_activated is True
    assert outcome.hard_failure is False
    assert not outcome.rom_path.exists()
    assert not outcome.summary_path.exists()
    assert any(
        "INMS TEST (MinC/2026-06): não ativado — dataset ausente "
        "(serviço não requisitado no período)" in warning
        for warning in exit_code.warnings
    )


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


_CATEGORIA_CONFIG_YAML = """\
indicator:
  id: INMS-01
  contractual_id: "INMS 1.1"
  name: Incidentes atendidos dentro do prazo

scope:
  contract: "40/2022 - Ministério da Cultura"
  orgao: MinC

source:
  csv: inms-01.csv
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
  base_points: 165
  step_points: 20
  step_size_pct: 0.1
"""

_CATEGORIAS_YAML = """\
categorias:
  ATENDIMENTO_N1:
    label: "Atendimento Remoto aos Usuários"
    inms:
      "1.1": {mode: grupo_executor, in_values: ["N1"]}
  OPERACAO_N3:
    label: "Operação e Sustentação da Infraestrutura de TI"
    inms:
      "1.1": {mode: grupo_executor, catch_all_contains: "(CIT)"}
"""

_CATEGORIA_RAW_CSV = (
    "Nº Solicitacao;DataHoraFim;No prazo;Grupo_executor\n"
    "1;2026-06-01;S;N1\n"
    "2;2026-06-02;S;N1\n"
    "3;2026-06-03;S;(CIT) - Infra\n"
)


def test_run_measure_ignores_split_derived_configs_on_disk(tmp_path: Path) -> None:
    """Regressão: `split` materializa `inms-01.<categoria>.yaml` no mesmo
    diretório do config base (ADR 0002). `run_measure` já expande as
    categorias em memória a partir do config base (Ticket 04) — se também
    redescobrir os YAMLs derivados pelo glob, reprocessa cada categoria de
    novo a partir do CSV já filtrado, produzindo ids compostos espúrios
    (`INMS-01.ATENDIMENTO_N1.ATENDIMENTO_N1` etc.)."""
    config_dir = tmp_path / "configs"
    data_dir = tmp_path / "input"
    output_dir = tmp_path / "roms"
    competencia_data_dir = data_dir / "2026" / "06"
    competencia_data_dir.mkdir(parents=True)
    config_dir.mkdir(parents=True)
    (config_dir / "inms-01.yaml").write_text(_CATEGORIA_CONFIG_YAML, encoding="utf-8")
    (config_dir / "categorias.yaml").write_text(_CATEGORIAS_YAML, encoding="utf-8")
    (competencia_data_dir / "inms-01.csv").write_text(_CATEGORIA_RAW_CSV, encoding="utf-8")

    split_result = run_split("2026-06", config_dir, data_dir, expected_orgao="MinC")
    assert split_result.status == "done"
    assert (config_dir / "inms-01.ATENDIMENTO_N1.yaml").exists()
    assert (config_dir / "inms-01.OPERACAO_N3.yaml").exists()

    result = run_measure("2026-06", config_dir, data_dir, output_dir, expected_orgao="MinC")

    assert result.status == "done"
    assert len(result.indicators) == 2
    written = {p.stem for p in (output_dir / "2026-06").glob("*.md")}
    assert written == {"INMS-01.ATENDIMENTO_N1", "INMS-01.OPERACAO_N3"}
