from pathlib import Path

from pyauditor.excel.capa import COMMON_FIELD_LABELS, ORGAO_FIELD_LABELS, bootstrap_capa_csv
from pyauditor.interactive.flow import collect_answers, run_guided_flow, select_commands
from tests.support.fake_interaction_provider import CANCEL, FakeInteractionProvider

OBJETOS_CSV = """Item;Categoria;Valor Mensal do Contrato 40/2022
1;Central de Serviços;"R$ 148.205,54"
2;GT dos Projetos e Operações;"R$ 77.654,90"
3;Banco de Dados;"R$ 43.888,89"
4;"Aplicações, virtualização";"R$ 59.694,54"
5;Serviços Corporativos;"R$ 21.035,21"
6;Armazenamento e Backup;"R$ 16.145,94"
7;Redes;"R$ 31.382,28"
8;"Segurança da Informação";"R$ 34.143,44"
9;DevOps;"R$ 28.912,84"
TOTAL MENSAL;;"R$ 461.063,58"
TOTAL ANUAL;;"R$ 5.532.762,96"
"""


def test_collect_answers_returns_scripted_values() -> None:
    provider = FakeInteractionProvider(
        answers=[
            "2026-06",  # competencia
            "MinC",  # orgao
            "configs",  # config_dir
            "input",  # data_dir
            "roms",  # output_dir
            "reports",  # report_dir
            "input/capa.csv",  # capa_path
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
            "2026-06", "MinC", "configs", "input", "roms", "reports", "input/capa.csv",
            False,  # first confirm: declined -> re-collect
            "2026-07", "MTur", "configs", "input", "roms", "reports", "input/capa.csv",
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
            "2026-06", "MinC", "configs", "input", "roms", "reports", "input/capa.csv",
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
            "MinC", "configs", "input", "roms", "reports", "input/capa.csv", True,
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
    bootstrap_capa_csv(tmp_path / "input" / "capa.csv", COMMON_FIELD_LABELS)
    bootstrap_capa_csv(tmp_path / "input" / "capa_MinC.csv", ORGAO_FIELD_LABELS)
    (tmp_path / "input" / "objetos.csv").write_text(OBJETOS_CSV, encoding="utf-8-sig")

    provider = FakeInteractionProvider(
        answers=[
            "2026-06", "MinC", "configs", "input", "roms", "reports", "input/capa.csv", True,
            ["bootstrap", "measure", "report"],
        ]
    )

    exit_code = run_guided_flow(provider)

    assert exit_code == 0
    assert len(provider.summaries) == 1
    assert all(e.status == "done" for e in provider.summaries[0].state.commands)