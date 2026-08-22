from dataclasses import replace
from io import StringIO
from pathlib import Path

from rich.console import Console

from pyauditor.orchestration.run import RunRequest, execute_run
from pyauditor.orchestration.summary import (
    exit_code_for_run,
    fmt_pt_br,
    render_summary,
)

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


_CATEGORIAS_YAML = """\
categorias:
  DUMMY:
    label: "dummy"
    inms:
      "1.99": {mode: whole_indicator}
"""


def _run(tmp_path: Path) -> RunRequest:
    (tmp_path / 'configs' / 'MinC').mkdir(parents=True)
    (tmp_path / 'input' / 'MinC' / '2026' / '06').mkdir(parents=True)
    (tmp_path / 'configs' / 'MinC' / 'inms-test.yaml').write_text(
        _CONFIG_YAML, encoding='utf-8'
    )
    (tmp_path / 'configs' / 'MinC' / 'categorias.yaml').write_text(
        _CATEGORIAS_YAML, encoding='utf-8'
    )
    (tmp_path / 'input' / 'MinC' / '2026' / '06' / 'data.csv').write_text(
        'Nº Solicitacao;DataHoraFim;No prazo\n1;2026-06-01;S\n2;2026-06-02;N\n',
        encoding='utf-8',
    )
    return RunRequest(
        competencia='2026-06',
        orgao='MinC',
        config_dir=tmp_path / 'configs',
        data_dir=tmp_path / 'input',
        output_dir=tmp_path / 'roms',
        report_dir=tmp_path / 'reports',
        capa_path=tmp_path / 'input' / 'capa.csv',
        runs_dir=tmp_path / '.pyauditor' / 'runs',
    )


def test_fmt_pt_br_formato_humano() -> None:
    # Ticket 06, Q5/Q6: formato humano pt-BR (milhar com ponto, decimal com
    # vírgula) — só no painel; logs/JSON mantém ponto decimal (máquina).
    assert fmt_pt_br(46909.85) == '46.909,85'
    assert fmt_pt_br(1.24) == '1,24'
    assert fmt_pt_br(0.0) == '0,00'
    assert fmt_pt_br(1234567.891) == '1.234.567,89'


def test_render_summary_prints_and_exit_code_is_4_for_unfilled_capa(
    tmp_path: Path,
) -> None:
    # A capa criada pelo bootstrap fica em branco — o report saí como rascunho
    # (não-publicável, ticket 02) E com glosa não calculada (sem valor mensal,
    # ticket 01) → pela precedência 1>4>3>0, o run termina em 4
    # (CÁLCULO FINANCEIRO INDISPONÍVEL), nunca `0`.
    run_result = execute_run(_run(tmp_path))

    buffer = StringIO()
    render_summary(
        run_result, console=Console(file=buffer, force_terminal=False)
    )

    assert exit_code_for_run(run_result.state.commands, run_result.results) == 4
    assert 'report' in buffer.getvalue()


def test_render_summary_shows_next_steps_for_pending_commands(
    tmp_path: Path,
) -> None:
    # Selecting only bootstrap leaves measure/report pending, with a known,
    # checkable reason ("rode `pyauditor measure`") for the "Próximos passos"
    # panel.
    request = replace(_run(tmp_path), commands=frozenset({'bootstrap'}))

    run_result = execute_run(request)

    buffer = StringIO()
    render_summary(
        run_result, console=Console(file=buffer, force_terminal=False)
    )

    output = buffer.getvalue()
    assert 'Próximos passos' in output
    assert 'measure' in output


def test_render_summary_points_to_incomplete_orgao_after_isolated_failure(
    tmp_path: Path,
) -> None:
    # Ticket 08 (Q3): quando um órgão fica incompleto (isolado por falha), o
    # painel "Próximos passos" aponta o comando exato para completá-lo sozinho.
    (tmp_path / 'configs' / 'MTur').mkdir(parents=True)
    (tmp_path / 'input' / 'MTur' / '2026' / '06').mkdir(parents=True)
    (tmp_path / 'configs' / 'MTur' / 'inms-test.yaml').write_text(
        _CONFIG_YAML.replace('orgao: MinC', 'orgao: MTur'), encoding='utf-8'
    )
    (tmp_path / 'input' / 'MTur' / '2026' / '06' / 'data.csv').write_text(
        'Nº Solicitacao;DataHoraFim;No prazo\n1;;S\n2;;N\n',
        encoding='utf-8',  # hard failure
    )
    request = replace(_run(tmp_path), orgao='both')

    run_result = execute_run(request, on_failure=lambda entry: 'isolate')

    buffer = StringIO()
    render_summary(
        run_result, console=Console(file=buffer, force_terminal=False)
    )

    output = buffer.getvalue()
    assert 'Próximos passos' in output
    assert 'MTur: relatório não gerado' in output
    assert 'execute `pyauditor run 2026-06 --orgao MTur`' in output


def test_render_summary_text_has_root_panel(tmp_path: Path) -> None:
    # Painel "Resultado" (Q3/Q9/Q10): status global + contagens + publicação.
    run_result = execute_run(_run(tmp_path))

    buffer = StringIO()
    render_summary(
        run_result, console=Console(file=buffer, force_terminal=False)
    )

    output = buffer.getvalue()
    assert 'Resultado' in output
    assert 'CÁLCULO FINANCEIRO INDISPONÍVEL' in output  # capa em branco (03:4)
    assert 'Competência' in output
    assert 'Glosa monetária' in output
    assert 'Publicação' in output
    assert 'Duração' in output
    assert 'Artefatos' in output


def test_summary_json_matches_exit_code(tmp_path: Path) -> None:
    from pyauditor.orchestration.summary import summary_json

    run_result = execute_run(_run(tmp_path))
    code = exit_code_for_run(run_result.state.commands, run_result.results)

    payload = summary_json(run_result, code)

    assert payload['codigo_saida'] == 4  # capa em branco -> glosa não calculada
    assert payload['resultado'] == 'CÁLCULO FINANCEIRO INDISPONÍVEL'
    assert payload['competencia'] == '2026-06'
    assert payload['orgaos']['MinC']['glosa'] == 'não calculada'
    assert payload['orgaos']['MinC']['publicable'] is False
    assert payload['publicacao']['liberada'] is False
    assert payload['avisos'] >= 0
    assert 'duracao_ms' in payload
    assert 'caminhos' in payload


def test_exit_code_for_run_precedence() -> None:
    from pyauditor.cli.consolidate import ConsolidateResult
    from pyauditor.cli.report import ReportResult
    from pyauditor.orchestration.state import CommandStateEntry

    done_measure = CommandStateEntry(
        command='measure', orgao='MinC', status='done'
    )
    done_report = CommandStateEntry(
        command='report', orgao='MinC', status='done'
    )
    done_consolidate = CommandStateEntry(
        command='consolidate', orgao=None, status='done'
    )
    skipped_report = CommandStateEntry(
        command='report', orgao='MinC', status='skipped'
    )
    skipped_measure = CommandStateEntry(
        command='measure', orgao='MinC', status='skipped'
    )
    errored = CommandStateEntry(
        command='consolidate', orgao=None, status='error'
    )

    ok_report = ReportResult(
        status='done',
        competencia='2026-06',
        orgao='MinC',
        output_path=Path('r.xlsx'),
        indicator_count=1,
        warnings=(),
        error_message=None,
        publicable=True,
        glosa_calculada=True,
    )
    draft_report = ReportResult(
        status='done',
        competencia='2026-06',
        orgao='MinC',
        output_path=Path('r.xlsx'),
        indicator_count=1,
        warnings=(),
        error_message=None,
        publicable=False,
        glosa_calculada=True,
    )
    glosa_missing = ConsolidateResult(
        status='done',
        competencia='2026-06',
        output_path=Path('c.xlsx'),
        decisions_preserved=0,
        warnings=(),
        error_message=None,
        glosa_calculada=False,
    )

    # 0 — tudo done e publicável, sem glosa pendente.
    assert exit_code_for_run((done_measure, done_report), (ok_report,)) == 0
    # 3 — report não-publicável (rascunho).
    assert exit_code_for_run((done_measure, done_report), (draft_report,)) == 3
    # 3 — etapa de produção skipped (não-produção faltante `0` antes).
    assert (
        exit_code_for_run(
            (done_measure, done_report, skipped_report), (ok_report,)
        )
        == 3
    )
    assert exit_code_for_run((done_measure, skipped_measure), ()) == 0
    # 4 — glosa não calculada vence 3/0.
    assert (
        exit_code_for_run(
            (done_measure, done_report, done_consolidate),
            (draft_report, glosa_missing),
        )
        == 4
    )
    # 1 — falha técnica vence 4.
    assert (
        exit_code_for_run(
            (done_measure, done_report, errored), (draft_report, glosa_missing)
        )
        == 1
    )
