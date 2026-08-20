from pathlib import Path

from pyauditor.excel.capa import bootstrap_capa
from pyauditor.interactive.flow import collect_answers, run_guided_flow, select_commands
from tests.support.fake_interaction_provider import CANCEL, FakeInteractionProvider


def test_collect_answers_returns_scripted_values() -> None:
    provider = FakeInteractionProvider(
        answers=[
            "2026-06",  # competencia
            "MinC",  # orgao
            "configs",  # config_dir
            "input",  # data_dir
            "roms",  # output_dir
            "reports",  # report_dir
            "capa.xlsx",  # capa_path
            True,  # confirm
        ]
    )

    answers = collect_answers(provider)

    assert answers.competencia == "2026-06"
    assert answers.orgao == "MinC"
    assert answers.config_dir == Path("configs")


def test_collect_answers_reentries_on_declined_confirmation() -> None:
    provider = FakeInteractionProvider(
        answers=[
            "2026-06", "MinC", "configs", "input", "roms", "reports", "capa.xlsx",
            False,  # first confirm: declined -> re-collect
            "2026-07", "MTur", "configs", "input", "roms", "reports", "capa.xlsx",
            True,
        ]
    )

    answers = collect_answers(provider)

    assert answers.competencia == "2026-07"
    assert answers.orgao == "MTur"


def test_cancel_during_collect_answers_exits_cleanly_without_raising() -> None:
    provider = FakeInteractionProvider(answers=["2026-06", CANCEL])

    exit_code = run_guided_flow(provider)

    assert exit_code == 130
    assert any("Encerrado" in text for text, _ in provider.messages)


def test_cancel_at_final_confirm_exits_instead_of_looping() -> None:
    provider = FakeInteractionProvider(
        answers=[
            "2026-06", "MinC", "configs", "input", "roms", "reports", "capa.xlsx",
            CANCEL,  # Ctrl+C at "Está correto?" — must exit, not loop as a fake "No"
        ]
    )

    exit_code = run_guided_flow(provider)

    assert exit_code == 130


def test_select_commands_disables_consolidate_when_not_both_orgaos() -> None:
    provider = FakeInteractionProvider(answers=[["bootstrap", "measure", "report"]])

    selected = select_commands(provider, "MinC")

    assert selected == frozenset({"bootstrap", "measure", "report"})


def test_help_token_shows_help_and_reasks() -> None:
    provider = FakeInteractionProvider(
        answers=[
            "?", "2026-06",  # competencia: help then real answer
            "MinC", "configs", "input", "roms", "reports", "capa.xlsx", True,
        ]
    )

    answers = collect_answers(provider)

    assert answers.competencia == "2026-06"
    assert provider.messages  # help text was shown


def test_run_guided_flow_end_to_end_happy_path(tmp_path: Path, monkeypatch: object) -> None:
    import os

    os.chdir(tmp_path)
    (tmp_path / "configs" / "MinC").mkdir(parents=True)
    (tmp_path / "input" / "MinC" / "2026" / "06").mkdir(parents=True)
    (tmp_path / "configs" / "MinC" / "inms-test.yaml").write_text(
        """\
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
""",
        encoding="utf-8",
    )
    (tmp_path / "input" / "MinC" / "2026" / "06" / "data.csv").write_text(
        "Nº Solicitacao;DataHoraFim;No prazo\n1;2026-06-01;S\n2;2026-06-02;N\n", encoding="utf-8"
    )
    bootstrap_capa(tmp_path / "capa.xlsx")

    provider = FakeInteractionProvider(
        answers=[
            "2026-06", "MinC", "configs", "input", "roms", "reports", "capa.xlsx", True,
            ["bootstrap", "measure", "report"],
        ]
    )

    exit_code = run_guided_flow(provider)

    assert exit_code == 0
    assert len(provider.summaries) == 1
    assert all(e.status == "done" for e in provider.summaries[0].state.commands)
