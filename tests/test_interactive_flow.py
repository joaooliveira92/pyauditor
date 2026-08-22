from pathlib import Path

from pyauditor.excel.capa import COMMON_FIELD_LABELS, ORGAO_FIELD_LABELS, bootstrap_capa_csv
from pyauditor.interactive.flow import collect_answers, run_guided_flow, select_commands
from tests.support.fake_interaction_provider import CANCEL, FakeInteractionProvider

OBJETOS_CSV = """Item,Categoria,Valor
1,Central de Serviços,"R$ 148.205,54"
2,GT dos Projetos e Operações,"R$ 77.654,90"
3,Banco de Dados,"R$ 43.888,89"
4,"Aplicações, virtualização","R$ 59.694,54"
5,Serviços Corporativos,"R$ 21.035,21"
6,Armazenamento e Backup,"R$ 16.145,94"
7,Redes,"R$ 31.382,28"
8,"Segurança da Informação","R$ 34.143,44"
9,DevOps,"R$ 28.912,84"
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
            "2026-06",
            "MinC",
            "configs",
            "input",
            "roms",
            "reports",
            "input/capa.csv",
            False,  # first confirm: declined -> re-collect
            "2026-07",
            "MTur",
            "configs",
            "input",
            "roms",
            "reports",
            "input/capa.csv",
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
    assert any("encerrada" in text for text, _ in provider.messages)


def test_cancel_at_final_confirm_exits_instead_of_looping() -> None:
    provider = FakeInteractionProvider(
        answers=[
            "2026-06",
            "MinC",
            "configs",
            "input",
            "roms",
            "reports",
            "input/capa.csv",
            CANCEL,  # Ctrl+C at "Está correto?" — must exit, not loop as a fake "No"
        ]
    )

    exit_code = run_guided_flow(provider)

    assert exit_code == 130


def test_select_commands_disables_consolidate_when_not_both_orgaos() -> None:
    provider = FakeInteractionProvider(answers=[["bootstrap", "split", "measure", "report"]])

    selected = select_commands(provider, "MinC")

    assert selected == frozenset({"bootstrap", "split", "measure", "report"})


def test_help_token_shows_help_and_reasks() -> None:
    provider = FakeInteractionProvider(
        answers=[
            "?",
            "2026-06",  # competencia: help then real answer
            "MinC",
            "configs",
            "input",
            "roms",
            "reports",
            "input/capa.csv",
            True,
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
""",
        encoding="utf-8",
    )
    (tmp_path / "configs" / "MinC" / "categorias.yaml").write_text(
        """\
categorias:
  DUMMY:
    label: "dummy"
    inms:
      "1.99": {mode: whole_indicator}
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
            "2026-06",
            "MinC",
            "configs",
            "input",
            "roms",
            "reports",
            "input/capa.csv",
            True,
            ["bootstrap", "split", "measure", "report"],
        ]
    )

    exit_code = run_guided_flow(provider)

    assert exit_code == 0
    assert len(provider.summaries) == 1
    assert all(e.status == "done" for e in provider.summaries[0].state.commands)


def test_force_commands_for_only_forces_selected_and_applicable() -> None:
    """`_force_commands_for`: report é forçado quando selecionado; consolidate
    só quando o plano é `both`; comandos não selecionados nunca são forçados."""
    from pyauditor.interactive.flow import _force_commands_for

    assert _force_commands_for("MinC", frozenset({"report"})) == frozenset({"report"})
    assert _force_commands_for(
        "both", frozenset({"report", "consolidate"})
    ) == frozenset({"report", "consolidate"})
    # MinC nunca força consolidate (disponível só em both).
    assert _force_commands_for("MinC", frozenset({"consolidate"})) == frozenset()
    assert _force_commands_for("MinC", frozenset({"measure"})) == frozenset()


def test_is_pre_dispatch_failure_recognizes_dependency_prefix() -> None:
    from pyauditor.interactive.flow import _is_pre_dispatch_failure
    from pyauditor.orchestration.state import CommandStateEntry

    failure = CommandStateEntry(
        command="report",
        orgao="MinC",
        status="error",
        started_at="2026-06-01T00:00:00+00:00",
        finished_at="2026-06-01T00:00:01+00:00",
        error_message="dependência não satisfeita: measure pendente",
    )
    technical = CommandStateEntry(
        command="report",
        orgao="MinC",
        status="error",
        started_at="2026-06-01T00:00:00+00:00",
        finished_at="2026-06-01T00:00:01+00:00",
        error_message="falha de escrita: disco cheio",
    )
    no_message = CommandStateEntry(
        command="report",
        orgao="MinC",
        status="error",
        started_at="2026-06-01T00:00:00+00:00",
        finished_at="2026-06-01T00:00:01+00:00",
    )

    assert _is_pre_dispatch_failure(failure) is True
    assert _is_pre_dispatch_failure(technical) is False
    assert _is_pre_dispatch_failure(no_message) is False


def test_select_commands_reselects_when_empty(tmp_path: Path) -> None:
    """Seleção vazia re-solicita até um conjunto não-vazio ser escolhido."""
    from pyauditor.interactive.flow import select_commands

    provider = FakeInteractionProvider(
        answers=[
            [],  # vazio → mostra aviso e re-cobra
            ["bootstrap", "measure"],
        ]
    )

    selected = select_commands(provider, "MinC")

    assert selected == frozenset({"bootstrap", "measure"})
    assert any("ao menos uma etapa" in text for text, _ in provider.messages)


def test_validate_competencia_rejects_invalid_period() -> None:
    from pyauditor.interactive.flow import _validate_competencia

    assert _validate_competencia("2026-06") is True
    invalid = _validate_competencia("2026-13")
    assert isinstance(invalid, str)
    assert "Competência inválida" in invalid
    assert _validate_competencia("?") is True  # help token aceito


def test_select_commands_unsupported_orgao_raises() -> None:
    from pyauditor.interactive.flow import select_commands

    provider = FakeInteractionProvider(answers=[["measure"]])
    try:
        select_commands(provider, "Mars")
    except ValueError as exc:
        assert "Seletor de órgão não suportado" in str(exc)
    else:
        raise AssertionError("esperava ValueError")


def test_state_presentation_renders_line(tmp_path: Path) -> None:
    from pyauditor.interactive.flow import _render_state_line
    from pyauditor.orchestration.state import CommandStateEntry

    entry = CommandStateEntry(command="measure", orgao="MinC", status="done")
    text, _style = _render_state_line(entry)
    assert "[x]" in text
    assert "measure (MinC)" in text
    assert _render_state_line(
        CommandStateEntry(command="report", orgao=None, status="pending")
    )[0] == "[ ] report (consolidado)"
