from dataclasses import replace
from pathlib import Path

from pyauditor.orchestration.run import FailureDecision, RunRequest, execute_run
from pyauditor.orchestration.state import CommandStateEntry, load_state, state_path

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


def _scaffold(tmp_path: Path, *, csv_body: str) -> RunRequest:
    config_dir = tmp_path / "configs"
    data_dir = tmp_path / "input"
    (config_dir / "MinC").mkdir(parents=True)
    (data_dir / "MinC" / "2026" / "06").mkdir(parents=True)
    (config_dir / "MinC" / "inms-test.yaml").write_text(_CONFIG_YAML, encoding="utf-8")
    (data_dir / "MinC" / "2026" / "06" / "data.csv").write_text(csv_body, encoding="utf-8")

    return RunRequest(
        competencia="2026-06",
        orgao="MinC",
        config_dir=config_dir,
        data_dir=data_dir,
        output_dir=tmp_path / "roms",
        report_dir=tmp_path / "reports",
        capa_path=tmp_path / "capa.xlsx",
        runs_dir=tmp_path / ".pyauditor" / "runs",
    )


_GOOD_CSV = "Nº Solicitacao;DataHoraFim;No prazo\n1;2026-06-01;S\n2;2026-06-02;N\n"
_HARD_FAILURE_CSV = "Nº Solicitacao;DataHoraFim;No prazo\n1;;S\n2;;N\n"


def _scaffold_both(tmp_path: Path, *, minc_csv: str, mtur_csv: str) -> RunRequest:
    config_dir = tmp_path / "configs"
    data_dir = tmp_path / "input"
    for orgao, csv_body in (("MinC", minc_csv), ("MTur", mtur_csv)):
        (config_dir / orgao).mkdir(parents=True)
        (data_dir / orgao / "2026" / "06").mkdir(parents=True)
        (config_dir / orgao / "inms-test.yaml").write_text(
            _CONFIG_YAML.replace("orgao: MinC", f"orgao: {orgao}"), encoding="utf-8"
        )
        (data_dir / orgao / "2026" / "06" / "data.csv").write_text(csv_body, encoding="utf-8")

    return RunRequest(
        competencia="2026-06",
        orgao="both",
        config_dir=config_dir,
        data_dir=data_dir,
        output_dir=tmp_path / "roms",
        report_dir=tmp_path / "reports",
        capa_path=tmp_path / "capa.xlsx",
        runs_dir=tmp_path / ".pyauditor" / "runs",
    )


def test_execute_run_happy_path_runs_bootstrap_measure_report_in_order(tmp_path: Path) -> None:
    request = _scaffold(tmp_path, csv_body=_GOOD_CSV)
    seen: list[tuple[str, str | None, str]] = []

    run_result = execute_run(
        request, on_state_change=lambda e: seen.append((e.command, e.orgao, e.status))
    )

    assert all(entry.status == "done" for entry in run_result.state.commands)
    assert len(run_result.results) == 3
    # bootstrap before measure before report, each reaching "done"
    done_order = [c for c, _, s in seen if s == "done"]
    assert done_order == ["bootstrap", "measure", "report"]


def test_execute_run_self_heals_from_a_corrupted_state_file(tmp_path: Path) -> None:
    request = _scaffold(tmp_path, csv_body=_GOOD_CSV)
    path = state_path(request.competencia, request.orgao, request.runs_dir)
    path.parent.mkdir(parents=True)
    path.write_text("not json", encoding="utf-8")

    run_result = execute_run(request)  # must not raise

    assert all(entry.status == "done" for entry in run_result.state.commands)


def test_execute_run_persists_state_and_resume_skips_done(tmp_path: Path) -> None:
    request = _scaffold(tmp_path, csv_body=_GOOD_CSV)
    execute_run(request)

    path = state_path(request.competencia, request.orgao, request.runs_dir)
    state = load_state(path)
    assert state is not None
    assert all(entry.status == "done" for entry in state.commands)

    calls: list[str] = []
    execute_run(request, on_state_change=lambda e: calls.append(e.command))

    assert calls == []  # nothing re-run — everything already "done"


def test_execute_run_cascades_skip_to_downstream_commands(tmp_path: Path) -> None:
    request = _scaffold(tmp_path, csv_body=_HARD_FAILURE_CSV)

    run_result = execute_run(request, on_failure=lambda entry: "skip")

    by_command = {(e.command, e.orgao): e.status for e in run_result.state.commands}
    assert by_command[("bootstrap", "MinC")] == "done"
    assert by_command[("measure", "MinC")] == "skipped"
    assert by_command[("report", "MinC")] == "skipped"  # cascaded — never ran


def test_execute_run_abort_stops_immediately_and_preserves_pending(tmp_path: Path) -> None:
    request = _scaffold(tmp_path, csv_body=_HARD_FAILURE_CSV)

    run_result = execute_run(request, on_failure=lambda entry: "abort")

    by_command = {(e.command, e.orgao): e.status for e in run_result.state.commands}
    assert by_command[("bootstrap", "MinC")] == "done"
    assert by_command[("measure", "MinC")] == "error"
    assert by_command[("report", "MinC")] == "pending"  # never reached


def test_execute_run_retry_re_dispatches_until_success(tmp_path: Path) -> None:
    request = _scaffold(tmp_path, csv_body=_HARD_FAILURE_CSV)
    data_path = request.data_dir / "MinC" / "2026" / "06" / "data.csv"

    attempts = {"n": 0}

    def on_failure(entry: CommandStateEntry) -> FailureDecision:
        attempts["n"] += 1
        if attempts["n"] == 1:
            data_path.write_text(_GOOD_CSV, encoding="utf-8")
            return "retry"
        return "abort"

    run_result = execute_run(request, on_failure=on_failure)

    by_command = {(e.command, e.orgao): e.status for e in run_result.state.commands}
    assert by_command[("measure", "MinC")] == "done"
    assert attempts["n"] == 1


def test_execute_run_pre_dispatch_failure_offers_no_retry_option_distinction(
    tmp_path: Path,
) -> None:
    """Selecting only `report` — bootstrap/measure never ran — makes the
    dependency check fail before `report` is ever dispatched. `started_at`
    stays `None`, distinguishing this from a post-dispatch `Result` failure."""
    request = replace(
        _scaffold(tmp_path, csv_body=_GOOD_CSV), commands=frozenset({"report"})
    )
    seen: list[CommandStateEntry] = []

    def on_failure(entry: CommandStateEntry) -> FailureDecision:
        seen.append(entry)
        return "abort"

    execute_run(request, on_failure=on_failure)

    assert len(seen) == 1
    assert seen[0].command == "report"
    assert seen[0].started_at is None
    assert seen[0].error_message is not None
    assert "dependência não satisfeita" in seen[0].error_message


def test_execute_run_pre_dispatch_failure_skip_cascades(tmp_path: Path) -> None:
    request = replace(
        _scaffold(tmp_path, csv_body=_GOOD_CSV), commands=frozenset({"report"})
    )

    run_result = execute_run(request, on_failure=lambda entry: "skip")

    by_command = {(e.command, e.orgao): e.status for e in run_result.state.commands}
    assert by_command[("bootstrap", "MinC")] == "skipped"  # not selected
    assert by_command[("measure", "MinC")] == "skipped"  # not selected
    assert by_command[("report", "MinC")] == "skipped"  # dependency-missing, skipped


def test_execute_run_pre_dispatch_failure_abort_preserves_error_entry(tmp_path: Path) -> None:
    request = replace(
        _scaffold(tmp_path, csv_body=_GOOD_CSV), commands=frozenset({"report"})
    )

    run_result = execute_run(request, on_failure=lambda entry: "abort")

    by_command = {(e.command, e.orgao): e.status for e in run_result.state.commands}
    assert by_command[("report", "MinC")] == "error"


def test_execute_run_both_orgaos_happy_path_runs_consolidate_last(tmp_path: Path) -> None:
    request = _scaffold_both(tmp_path, minc_csv=_GOOD_CSV, mtur_csv=_GOOD_CSV)
    seen: list[tuple[str, str | None, str]] = []

    run_result = execute_run(
        request, on_state_change=lambda e: seen.append((e.command, e.orgao, e.status))
    )

    assert all(entry.status == "done" for entry in run_result.state.commands)
    done_order = [c for c, _, s in seen if s == "done"]
    assert done_order == [
        "bootstrap", "bootstrap", "measure", "measure", "report", "report", "consolidate",
    ]


def test_execute_run_both_orgaos_cascades_skip_into_shared_consolidate(tmp_path: Path) -> None:
    request = _scaffold_both(tmp_path, minc_csv=_HARD_FAILURE_CSV, mtur_csv=_GOOD_CSV)

    run_result = execute_run(request, on_failure=lambda entry: "skip")

    by_command = {(e.command, e.orgao): e.status for e in run_result.state.commands}
    assert by_command[("measure", "MinC")] == "skipped"
    assert by_command[("report", "MinC")] == "skipped"  # cascaded from measure/MinC
    assert by_command[("measure", "MTur")] == "done"
    assert by_command[("report", "MTur")] == "done"
    assert by_command[("consolidate", None)] == "skipped"  # cascaded cross-órgão
