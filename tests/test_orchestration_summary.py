from dataclasses import replace
from decimal import Decimal
from io import StringIO
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st
from rich.console import Console

from pyauditor.orchestration.run import RunRequest, execute_run
from pyauditor.orchestration.summary import (
    exit_code_for_run,
    fmt_pt_br,
    render_summary,
)


def _unlocalize(fmt: str) -> str:
    """Undo pt-BR separators, returning a standard ``<int>.<frac>`` string."""
    if ',' in fmt:
        integer_part, _, fractional_part = fmt.partition(',')
        return f'{integer_part.replace(".", "")}.{fractional_part}'
    return fmt.replace('.', '')


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
    # Ticket 06, Q5/Q7: formato humano pt-BR (milhar com ponto, decimal com
    # vírgula) — só exato; logs/JSON mantém ponto decimal (máquina).
    assert fmt_pt_br(46909.85) == '46.909,85'
    assert fmt_pt_br(1.24) == '1,24'
    assert fmt_pt_br(0.0) == '0,00'
    assert fmt_pt_br(1234567.891) == '1.234.567,89'


@given(
    st.floats(
        min_value=0.001, max_value=1e12, allow_nan=False, allow_infinity=False
    )
)
@settings(max_examples=150, deadline=10000)
def test_fmt_pt_br_float_round_trips(v: float) -> None:
    for decimals in (0, 1, 2, 3, 6):
        assert _unlocalize(fmt_pt_br(v, decimals=decimals)) == (
            f'{v:.{decimals}f}'
        )


@given(st.integers(min_value=0, max_value=9_999_999_999))
@settings(max_examples=100, deadline=10000)
def test_fmt_pt_br_groups_thousands_by_three(n: int) -> None:
    localized = fmt_pt_br(float(n), decimals=0)
    integer_part = localized.partition(',')[0]
    if n < 1000:
        assert integer_part == str(n)
        return
    groups = integer_part.split('.')
    assert all(len(group) == 3 for group in groups[1:])


@given(
    st.floats(
        min_value=-1e12, max_value=-0.001, allow_nan=False, allow_infinity=False
    )
)
@settings(max_examples=150, deadline=10000)
def test_fmt_pt_br_negative_sign_is_preserved(v: float) -> None:
    for decimals in (0, 2):
        assert fmt_pt_br(v, decimals=decimals).startswith('-')


@given(
    st.integers(min_value=-1_000_000_000_000, max_value=1_000_000_000_000),
    st.integers(min_value=1, max_value=1000),
)
@settings(max_examples=150, deadline=10000)
def test_fmt_pt_br_decimal_round_trips(
    numerator: int, denominator: int
) -> None:
    v = Decimal(numerator) / Decimal(denominator)
    for decimals in (0, 2, 4):
        assert _unlocalize(fmt_pt_br(v, decimals=decimals)) == format(
            v, f'.{decimals}f'
        )


def test_fmt_pt_br_rejects_non_numeric_values() -> None:
    import pytest

    with pytest.raises(TypeError):
        fmt_pt_br('12.5')  # ty: ignore[invalid-argument-type]
    with pytest.raises(TypeError):
        fmt_pt_br(None)  # ty: ignore[invalid-argument-type]
    with pytest.raises(TypeError):
        fmt_pt_br(True)
    with pytest.raises(TypeError):
        fmt_pt_br(1, decimals=True)
    with pytest.raises(TypeError):
        fmt_pt_br(1, decimals='2')  # ty: ignore[invalid-argument-type]


def test_fmt_pt_br_rejects_non_finite_and_negative_decimals() -> None:
    import math

    import pytest

    for value in (float('inf'), float('-inf'), float('nan')):
        with pytest.raises(ValueError):
            fmt_pt_br(value)
    with pytest.raises(ValueError):
        fmt_pt_br(Decimal('Infinity'))
    with pytest.raises(ValueError):
        fmt_pt_br(Decimal('NaN'))
    with pytest.raises(ValueError):
        fmt_pt_br(1, decimals=-1)
    assert math.isfinite(float(fmt_pt_br(0.0).replace(',', '.')))


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


def test_all_warnings_serializes_target() -> None:
    from dataclasses import dataclass, field

    from pyauditor.categoria_filter import Warning, WarningTarget
    from pyauditor.orchestration.summary_json import _all_warnings

    @dataclass
    class _FakeResult:
        warnings: tuple[Warning, ...] = field(default_factory=tuple)

    @dataclass
    class _FakeRunResult:
        results: tuple[_FakeResult, ...]

    with_target = Warning(
        code='in_values_unmatched',
        message='...',
        orgao='MinC',
        competencia='2026-06',
        inms_key='1.1',
        categoria='ATENDIMENTO_N1',
        target=WarningTarget(
            family='categorias',
            orgao='MinC',
            path=(
                'config',
                'categorias',
                'ATENDIMENTO_N1',
                'inms',
                '1.1',
                'in_values',
            ),
        ),
    )
    without_target = Warning(
        code='outros_leftover',
        message='...',
        orgao='MTur',
        competencia='2026-07',
        inms_key='1.1',
        categoria='outros',
    )

    result = _FakeResult(warnings=(with_target, without_target))
    payload = _all_warnings(_FakeRunResult(results=(result,)))  # ty: ignore[invalid-argument-type]

    assert payload[0]['target'] == {
        'family': 'categorias',
        'orgao': 'MinC',
        'path': [
            'config',
            'categorias',
            'ATENDIMENTO_N1',
            'inms',
            '1.1',
            'in_values',
        ],
    }
    assert payload[1]['target'] is None


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


def test_artifact_line_describes_each_result_type() -> None:
    from pathlib import Path

    from pyauditor.cli.measure_contracts import IndicatorOutcome
    from pyauditor.commands.contracts import (
        BootstrapResult,
        ConsolidateResult,
        MeasureResult,
        ReportResult,
        SplitResult,
    )
    from pyauditor.orchestration.state import CommandStateEntry
    from pyauditor.orchestration.summary import _artifact_line

    done = CommandStateEntry(command='x', orgao='MinC', status='done')

    assert (
        _artifact_line(
            done,
            BootstrapResult(
                status='done',
                orgao='MinC',
                capa_path=Path('in/capa.csv'),
                created=True,
                warnings=(),
                error_message=None,
            ),
        )
        == 'in/capa.csv'
    )

    assert (
        _artifact_line(
            done,
            SplitResult(
                status='done',
                competencia='2026-06',
                orgao='MinC',
                categorias=(),
                warnings=(),
                error_message=None,
                sintetico_path=Path('out/sintetico.xlsx'),
            ),
        )
        == '0 categoria(s) processada(s) | out/sintetico.xlsx'
    )

    assert (
        _artifact_line(
            done,
            MeasureResult(
                status='done',
                competencia='2026-06',
                orgao='MinC',
                indicators=(
                    IndicatorOutcome(
                        contractual_id='A1',
                        rom_path=Path('r.rom'),
                        summary_path=Path('s.rom'),
                        hard_failure=True,
                        error=None,
                    ),
                    IndicatorOutcome(
                        contractual_id='B2',
                        rom_path=Path('r.rom'),
                        summary_path=Path('s.rom'),
                        hard_failure=False,
                        error=None,
                    ),
                ),
                warnings=(),
                error_message=None,
            ),
        )
        == '2 indicador(es) apurado(s) | falhas: A1'
    )

    assert (
        _artifact_line(
            done,
            ReportResult(
                status='done',
                competencia='2026-06',
                orgao='MinC',
                output_path=Path('r.xlsx'),
                indicator_count=3,
                warnings=(),
                error_message=None,
            ),
        )
        == 'r.xlsx (3 indicadores)'
    )

    assert (
        _artifact_line(
            done,
            ConsolidateResult(
                status='done',
                competencia='2026-06',
                output_path=Path('c.xlsx'),
                decisions_preserved=5,
                warnings=(),
                error_message=None,
            ),
        )
        == 'c.xlsx (5 decisão(ões) preservada(s))'
    )


def test_artifact_line_falls_back_for_missing_results() -> None:
    from pyauditor.orchestration.state import CommandStateEntry
    from pyauditor.orchestration.summary import _artifact_line

    skipped = CommandStateEntry(
        command='report', orgao='MinC', status='skipped'
    )
    done = CommandStateEntry(command='report', orgao='MinC', status='done')
    pending = CommandStateEntry(
        command='measure', orgao='MinC', status='pending'
    )

    assert _artifact_line(skipped, None) == 'pulado'
    assert _artifact_line(done, None) == 'resultado indisponível ou ambíguo'
    assert _artifact_line(pending, None) == '-'


def test_render_summary_json_emits_plain_document(tmp_path: Path) -> None:
    import json

    run_result = execute_run(_run(tmp_path))

    buffer = StringIO()
    render_summary(
        run_result,
        output='json',
        console=Console(file=buffer, force_terminal=False),
    )

    payload = json.loads(buffer.getvalue())
    assert payload['codigo_saida'] == 4
    assert 'competencia' in payload
    assert 'orgaos' in payload


def test_render_summary_rejects_unsupported_output_format(
    tmp_path: Path,
) -> None:
    import pytest

    run_result = execute_run(_run(tmp_path))

    with pytest.raises(ValueError, match='Unsupported summary output format'):
        render_summary(
            run_result,
            output='xml',  # ty: ignore[invalid-argument-type]
            console=Console(file=StringIO(), force_terminal=False),
        )
