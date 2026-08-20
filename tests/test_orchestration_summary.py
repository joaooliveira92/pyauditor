from dataclasses import replace
from io import StringIO
from pathlib import Path

from rich.console import Console

from pyauditor.orchestration.run import RunRequest, execute_run
from pyauditor.orchestration.summary import exit_code_for_run, render_summary

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


def _run(tmp_path: Path) -> RunRequest:
    (tmp_path / "configs" / "MinC").mkdir(parents=True)
    (tmp_path / "input" / "MinC" / "2026" / "06").mkdir(parents=True)
    (tmp_path / "configs" / "MinC" / "inms-test.yaml").write_text(_CONFIG_YAML, encoding="utf-8")
    (tmp_path / "input" / "MinC" / "2026" / "06" / "data.csv").write_text(
        "Nº Solicitacao;DataHoraFim;No prazo\n1;2026-06-01;S\n2;2026-06-02;N\n", encoding="utf-8"
    )
    return RunRequest(
        competencia="2026-06",
        orgao="MinC",
        config_dir=tmp_path / "configs",
        data_dir=tmp_path / "input",
        output_dir=tmp_path / "roms",
        report_dir=tmp_path / "reports",
        capa_path=tmp_path / "capa.xlsx",
        runs_dir=tmp_path / ".pyauditor" / "runs",
    )


def test_render_summary_prints_and_exit_code_is_0_when_all_done(tmp_path: Path) -> None:
    run_result = execute_run(_run(tmp_path))

    buffer = StringIO()
    render_summary(run_result, console=Console(file=buffer, force_terminal=False))

    assert exit_code_for_run(run_result.state.commands) == 0
    assert "report" in buffer.getvalue()


def test_render_summary_shows_next_steps_for_pending_commands(tmp_path: Path) -> None:
    # Selecting only bootstrap leaves measure/report pending, with a known,
    # checkable reason ("rode `pyauditor measure`") for the "Próximos passos" panel.
    request = replace(_run(tmp_path), commands=frozenset({"bootstrap"}))

    run_result = execute_run(request)

    buffer = StringIO()
    render_summary(run_result, console=Console(file=buffer, force_terminal=False))

    output = buffer.getvalue()
    assert "Próximos passos" in output
    assert "measure" in output


def test_exit_code_for_run_is_1_iff_any_command_errored() -> None:
    from pyauditor.orchestration.state import CommandStateEntry

    ok = (
        CommandStateEntry(command="bootstrap", orgao="MinC", status="done"),
        CommandStateEntry(command="measure", orgao="MinC", status="skipped"),
    )
    assert exit_code_for_run(ok) == 0

    with_error = (
        CommandStateEntry(command="bootstrap", orgao="MinC", status="done"),
        CommandStateEntry(command="measure", orgao="MinC", status="error"),
    )
    assert exit_code_for_run(with_error) == 1
