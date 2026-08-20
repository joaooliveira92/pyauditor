from pathlib import Path

from pyauditor.cli.run import run_run

_CONFIG_YAML = """\
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


def test_run_run_executes_pipeline_and_returns_4_for_unfilled_capa(tmp_path: Path) -> None:
    (tmp_path / "configs" / "MinC").mkdir(parents=True)
    (tmp_path / "input" / "MinC" / "2026" / "06").mkdir(parents=True)
    (tmp_path / "configs" / "MinC" / "inms-test.yaml").write_text(_CONFIG_YAML, encoding="utf-8")
    (tmp_path / "input" / "MinC" / "2026" / "06" / "data.csv").write_text(
        "Nº Solicitacao;DataHoraFim;No prazo\n1;2026-06-01;S\n2;2026-06-02;N\n", encoding="utf-8"
    )

    exit_code = run_run(
        competencia="2026-06",
        orgao="MinC",
        config_dir=tmp_path / "configs",
        data_dir=tmp_path / "input",
        output_dir=tmp_path / "roms",
        report_dir=tmp_path / "reports",
        capa_path=tmp_path / "capa.xlsx",
        runs_dir=tmp_path / ".pyauditor" / "runs",
    )
    # Capa em branco criada pelo bootstrap: relatório rascunho (3) + glosa não
    # calculada (4) → 4 vence pela precedência; nunca 0.
    assert exit_code == 4
    assert (tmp_path / "reports" / "relatorio_2026-06_MinC.xlsx").exists()
