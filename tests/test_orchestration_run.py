import shutil
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pyauditor.orchestration.run import (
    FailureDecision,
    RunRequest,
    execute_run,
    isolate_on_failure,
)
from pyauditor.orchestration.state import (
    CommandStateEntry,
    load_state,
    state_path,
)

_CONFIG_YAML = """\
indicator:
  id: INMS-99
  contractual_id: "INMS 1.99"
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


def _scaffold(tmp_path: Path, *, csv_body: str) -> RunRequest:
    config_dir = tmp_path / 'configs'
    data_dir = tmp_path / 'input'
    (config_dir / 'MinC').mkdir(parents=True)
    (data_dir / 'MinC' / '2026' / '06').mkdir(parents=True)
    (config_dir / 'MinC' / 'inms-99.yaml').write_text(
        _CONFIG_YAML, encoding='utf-8'
    )
    (config_dir / 'MinC' / 'categorias.yaml').write_text(
        _CATEGORIAS_YAML, encoding='utf-8'
    )
    (data_dir / 'MinC' / '2026' / '06' / 'data.csv').write_text(
        csv_body, encoding='utf-8'
    )

    return RunRequest(
        competencia='2026-06',
        orgao='MinC',
        config_dir=config_dir,
        data_dir=data_dir,
        output_dir=tmp_path / 'roms',
        report_dir=tmp_path / 'reports',
        capa_path=data_dir / 'capa.csv',
        runs_dir=tmp_path / '.pyauditor' / 'runs',
    )


_GOOD_CSV = (
    'Nº Solicitacao;DataHoraFim;No prazo\n1;2026-06-01;S\n2;2026-06-02;N\n'
)
_HARD_FAILURE_CSV = 'Nº Solicitacao;DataHoraFim;No prazo\n1;;S\n2;;N\n'


def _scaffold_both(
    tmp_path: Path, *, minc_csv: str, mtur_csv: str
) -> RunRequest:
    config_dir = tmp_path / 'configs'
    data_dir = tmp_path / 'input'
    for orgao, csv_body in (('MinC', minc_csv), ('MTur', mtur_csv)):
        (config_dir / orgao).mkdir(parents=True)
        (data_dir / orgao / '2026' / '06').mkdir(parents=True)
        (config_dir / orgao / 'inms-99.yaml').write_text(
            _CONFIG_YAML.replace('orgao: MinC', f'orgao: {orgao}'),
            encoding='utf-8',
        )
        (config_dir / orgao / 'categorias.yaml').write_text(
            _CATEGORIAS_YAML, encoding='utf-8'
        )
        (data_dir / orgao / '2026' / '06' / 'data.csv').write_text(
            csv_body, encoding='utf-8'
        )

    return RunRequest(
        competencia='2026-06',
        orgao='both',
        config_dir=config_dir,
        data_dir=data_dir,
        output_dir=tmp_path / 'roms',
        report_dir=tmp_path / 'reports',
        capa_path=data_dir / 'capa.csv',
        runs_dir=tmp_path / '.pyauditor' / 'runs',
    )


def test_execute_run_happy_path_runs_bootstrap_measure_report_in_order(
    tmp_path: Path,
) -> None:
    request = _scaffold(tmp_path, csv_body=_GOOD_CSV)
    seen: list[tuple[str, str | None, str]] = []

    run_result = execute_run(
        request,
        on_state_change=lambda e: seen.append((e.command, e.orgao, e.status)),
    )

    assert all(entry.status == 'done' for entry in run_result.state.commands)
    assert len(run_result.results) == 4
    # bootstrap before split before measure before report, each reaching "done"
    done_order = [c for c, _, s in seen if s == 'done']
    assert done_order == ['bootstrap', 'split', 'measure', 'report']


def test_execute_run_self_heals_from_a_corrupted_state_file(
    tmp_path: Path,
) -> None:
    request = _scaffold(tmp_path, csv_body=_GOOD_CSV)
    path = state_path(request.competencia, request.orgao, request.runs_dir)
    path.parent.mkdir(parents=True)
    path.write_text('not json', encoding='utf-8')

    run_result = execute_run(request)  # must not raise

    assert all(entry.status == 'done' for entry in run_result.state.commands)


def test_execute_run_persists_state_and_resume_skips_done(
    tmp_path: Path,
) -> None:
    request = _scaffold(tmp_path, csv_body=_GOOD_CSV)
    execute_run(request)

    path = state_path(request.competencia, request.orgao, request.runs_dir)
    state = load_state(path)
    assert state is not None
    assert all(entry.status == 'done' for entry in state.commands)

    calls: list[str] = []
    execute_run(request, on_state_change=lambda e: calls.append(e.command))

    assert calls == []  # nothing re-run — everything already "done"


def test_execute_run_resume_redispatches_measure_when_roms_deleted(
    tmp_path: Path,
) -> None:
    """A persisted "done" only means "skip me" while the artifact is still
    on disk — a human running `rm -rf roms/` without also clearing
    `.pyauditor/runs/` must not leave `measure` skipped and `report` failing
    against ROMs that resume thinks still exist."""
    request = _scaffold(tmp_path, csv_body=_GOOD_CSV)
    execute_run(request)
    shutil.rmtree(request.output_dir)

    calls: list[str] = []
    run_result = execute_run(
        request, on_state_change=lambda e: calls.append(e.command)
    )

    assert 'measure' in calls
    assert all(entry.status == 'done' for entry in run_result.state.commands)
    assert (request.output_dir / 'MinC' / '2026-06').is_dir()


def test_execute_run_resume_redispatches_split_when_sintetico_deleted(
    tmp_path: Path,
) -> None:
    request = _scaffold(tmp_path, csv_body=_GOOD_CSV)
    execute_run(request)
    sintetico_path = request.report_dir / 'MinC' / '2026-06' / 'sintetico.xlsx'
    assert sintetico_path.exists()
    sintetico_path.unlink()

    calls: list[str] = []
    run_result = execute_run(
        request, on_state_change=lambda e: calls.append(e.command)
    )

    assert 'split' in calls
    assert all(entry.status == 'done' for entry in run_result.state.commands)
    assert sintetico_path.exists()


def test_execute_run_resume_redispatches_bootstrap_when_capa_deleted(
    tmp_path: Path,
) -> None:
    request = _scaffold(tmp_path, csv_body=_GOOD_CSV)
    execute_run(request)
    (request.data_dir / 'capa_MinC.csv').unlink()

    calls: list[str] = []
    run_result = execute_run(
        request, on_state_change=lambda e: calls.append(e.command)
    )

    assert 'bootstrap' in calls
    assert all(entry.status == 'done' for entry in run_result.state.commands)
    assert (request.data_dir / 'capa_MinC.csv').exists()


def test_execute_run_force_reruns_commands_marked_done(tmp_path: Path) -> None:
    request = _scaffold(tmp_path, csv_body=_GOOD_CSV)
    execute_run(request)

    path = state_path(request.competencia, request.orgao, request.runs_dir)
    state = load_state(path)
    assert state is not None
    assert all(entry.status == 'done' for entry in state.commands)

    calls: list[str] = []
    execute_run(
        replace(request, force=True),
        on_state_change=lambda e: calls.append(e.command),
    )

    assert (
        calls != []
    )  # force re-runs what the persisted state already marked done
    rerun_state = execute_run(replace(request, force=True)).state
    assert all(entry.status == 'done' for entry in rerun_state.commands)


def test_execute_run_cascades_skip_to_downstream_commands(
    tmp_path: Path,
) -> None:
    request = _scaffold(tmp_path, csv_body=_HARD_FAILURE_CSV)

    run_result = execute_run(request, on_failure=lambda entry: 'skip')

    by_command = {
        (e.command, e.orgao): e.status for e in run_result.state.commands
    }
    assert by_command['bootstrap', 'MinC'] == 'done'
    assert by_command['measure', 'MinC'] == 'skipped'
    assert by_command['report', 'MinC'] == 'skipped'  # cascaded — never ran


def test_execute_run_abort_stops_immediately_and_preserves_pending(
    tmp_path: Path,
) -> None:
    request = _scaffold(tmp_path, csv_body=_HARD_FAILURE_CSV)

    run_result = execute_run(request, on_failure=lambda entry: 'abort')

    by_command = {
        (e.command, e.orgao): e.status for e in run_result.state.commands
    }
    assert by_command['bootstrap', 'MinC'] == 'done'
    assert by_command['measure', 'MinC'] == 'error'
    assert by_command['report', 'MinC'] == 'pending'  # never reached


def test_execute_run_retry_re_dispatches_until_success(tmp_path: Path) -> None:
    request = _scaffold(tmp_path, csv_body=_HARD_FAILURE_CSV)
    data_path = request.data_dir / 'MinC' / '2026' / '06' / 'data.csv'

    attempts = {'n': 0}

    def on_failure(entry: CommandStateEntry) -> FailureDecision:
        attempts['n'] += 1
        if attempts['n'] == 1:
            data_path.write_text(_GOOD_CSV, encoding='utf-8')
            return 'retry'
        return 'abort'

    run_result = execute_run(request, on_failure=on_failure)

    by_command = {
        (e.command, e.orgao): e.status for e in run_result.state.commands
    }
    assert by_command['measure', 'MinC'] == 'done'
    assert attempts['n'] == 1


def test_execute_run_pre_dispatch_failure_offers_no_retry_option_distinction(
    tmp_path: Path,
) -> None:
    """Selecting only `report` — bootstrap/measure never ran — makes the
    dependency check fail before `report` is ever dispatched. The persisted
    entry is distinguished from a post-dispatch `Result` failure by its
    ``dependência não satisfeita`` message (state schema requires
    ``started_at``/``finished_at`` for every ``error`` entry)."""
    request = replace(
        _scaffold(tmp_path, csv_body=_GOOD_CSV), commands=frozenset({'report'})
    )
    seen: list[CommandStateEntry] = []

    def on_failure(entry: CommandStateEntry) -> FailureDecision:
        seen.append(entry)
        return 'abort'

    execute_run(request, on_failure=on_failure)

    assert len(seen) == 1
    assert seen[0].command == 'report'
    assert seen[0].status == 'error'
    assert seen[0].error_message is not None
    assert seen[0].error_message.startswith('dependência não satisfeita')


def test_execute_run_pre_dispatch_failure_skip_cascades(tmp_path: Path) -> None:
    request = replace(
        _scaffold(tmp_path, csv_body=_GOOD_CSV), commands=frozenset({'report'})
    )

    run_result = execute_run(request, on_failure=lambda entry: 'skip')

    by_command = {
        (e.command, e.orgao): e.status for e in run_result.state.commands
    }
    assert by_command['bootstrap', 'MinC'] == 'skipped'  # not selected
    assert by_command['measure', 'MinC'] == 'skipped'  # not selected
    assert (
        by_command['report', 'MinC'] == 'skipped'
    )  # dependency-missing, skipped


def test_execute_run_pre_dispatch_failure_abort_preserves_error_entry(
    tmp_path: Path,
) -> None:
    request = replace(
        _scaffold(tmp_path, csv_body=_GOOD_CSV), commands=frozenset({'report'})
    )

    run_result = execute_run(request, on_failure=lambda entry: 'abort')

    by_command = {
        (e.command, e.orgao): e.status for e in run_result.state.commands
    }
    assert by_command['report', 'MinC'] == 'error'


def test_execute_run_uses_shared_manifest_when_both_exist(
    tmp_path: Path,
) -> None:
    """Issue 01 — fonte única: com `datasets.yaml` em `_shared` e no per-órgão,
    o `run` (assim como o `measure`) resolve o manifest de `_shared`, não o
    per-órgão. Hoje o `_dispatch` do `run` prefere o per-órgão, divergindo do
    `cli/main.py`."""
    config_dir = tmp_path / 'configs'
    data_dir = tmp_path / 'input'
    (config_dir / '_shared').mkdir(parents=True)
    (config_dir / 'MinC').mkdir(parents=True)
    (config_dir / '_shared' / 'datasets.yaml').write_text(
        "datasets:\n  telefonemas:\n    file: tel.csv\n    delimiter: ';'\n",
        encoding='utf-8',
    )
    (config_dir / 'MinC' / 'datasets.yaml').write_text(
        "datasets:\n  telefonemas:\n    file: tel.csv\n    delimiter: ','\n",
        encoding='utf-8',
    )
    request = RunRequest(
        competencia='2026-06',
        orgao='MinC',
        config_dir=config_dir,
        data_dir=data_dir,
        output_dir=tmp_path / 'roms',
        report_dir=tmp_path / 'reports',
        capa_path=data_dir / 'capa.csv',
        runs_dir=tmp_path / '.pyauditor' / 'runs',
        commands=frozenset({'measure'}),
    )
    with patch(
        'pyauditor.orchestration.command_dispatch.run_measure',
        return_value=SimpleNamespace(status='done', error_message=None),
    ) as m:
        run_result = execute_run(request)

    by_command = {
        (e.command, e.orgao): e.status for e in run_result.state.commands
    }
    assert by_command['measure', 'MinC'] == 'done'
    manifest = m.call_args.kwargs['manifest']
    assert manifest is not None
    assert manifest.resolve('telefonemas').delimiter == ';'


def test_execute_run_both_orgaos_happy_path_runs_consolidate_last(
    tmp_path: Path,
) -> None:
    request = _scaffold_both(tmp_path, minc_csv=_GOOD_CSV, mtur_csv=_GOOD_CSV)
    seen: list[tuple[str, str | None, str]] = []

    run_result = execute_run(
        request,
        on_state_change=lambda e: seen.append((e.command, e.orgao, e.status)),
    )

    assert all(entry.status == 'done' for entry in run_result.state.commands)
    done_order = [c for c, _, s in seen if s == 'done']
    assert done_order == [
        'bootstrap',
        'bootstrap',
        'split',
        'split',
        'measure',
        'measure',
        'report',
        'report',
        'consolidate',
    ]


def test_execute_run_both_orgaos_cascades_skip_into_shared_consolidate(
    tmp_path: Path,
) -> None:
    request = _scaffold_both(
        tmp_path, minc_csv=_HARD_FAILURE_CSV, mtur_csv=_GOOD_CSV
    )

    run_result = execute_run(request, on_failure=lambda entry: 'skip')

    by_command = {
        (e.command, e.orgao): e.status for e in run_result.state.commands
    }
    assert by_command['measure', 'MinC'] == 'skipped'
    assert (
        by_command['report', 'MinC'] == 'skipped'
    )  # cascaded from measure/MinC
    assert by_command['measure', 'MTur'] == 'done'
    assert by_command['report', 'MTur'] == 'done'
    assert by_command['consolidate', None] == 'skipped'  # cascaded cross-órgão


def test_execute_run_isolate_on_split_failure_blocks_only_that_orgaos_measure(
    tmp_path: Path,
) -> None:
    """Ticket "04 - Integrar split em run/máquina de estado": `split` errando
    num órgão (aqui, `categorias.yaml` ausente pro MinC) isola só
    `measure`/`report` daquele órgão + o `consolidate` compartilhado — o MTur
    roda `bootstrap`→`split`→`measure`→`report` normalmente."""
    request = _scaffold_both(tmp_path, minc_csv=_GOOD_CSV, mtur_csv=_GOOD_CSV)
    (request.config_dir / 'MinC' / 'categorias.yaml').unlink()

    run_result = execute_run(request, on_failure=isolate_on_failure)

    by_command = {
        (e.command, e.orgao): e.status for e in run_result.state.commands
    }
    assert by_command['bootstrap', 'MinC'] == 'done'
    assert by_command['split', 'MinC'] == 'error'
    assert by_command['measure', 'MinC'] == 'skipped'
    assert by_command['report', 'MinC'] == 'skipped'
    assert by_command['bootstrap', 'MTur'] == 'done'
    assert by_command['split', 'MTur'] == 'done'
    assert by_command['measure', 'MTur'] == 'done'
    assert by_command['report', 'MTur'] == 'done'
    assert by_command['consolidate', None] == 'skipped'


def test_execute_run_measure_reused_split_does_not_suppress_in_values_warnings(
    tmp_path: Path,
) -> None:
    """Ticket 11 — `already_split` reflete a passada atual, não o estado
    persistido: se `split` foi reutilizado (done numa invocação anterior) e só
    `measure` re-executou, os avisos de `in_values`/`outros` NÃO são
    suprimidos — `split` não os emitiu nesta passada."""
    request = _scaffold(tmp_path, csv_body=_GOOD_CSV)
    with patch(
        'pyauditor.orchestration.command_dispatch.run_measure',
        return_value=SimpleNamespace(status='done', error_message=None),
    ):
        execute_run(request)

    # Segunda invocação: `split` está persistido como done — reutilizado, não
    # executado nesta passada. `measure` roda de novo (force_commands) com
    # already_split=False, então os avisos não são silenciados.
    resumed = replace(request, force_commands=frozenset({'measure'}))
    with patch(
        'pyauditor.orchestration.command_dispatch.run_measure',
        return_value=SimpleNamespace(status='done', error_message=None),
    ) as m2:
        execute_run(resumed)

    assert m2.call_args.kwargs['already_split'] is False


def test_execute_run_measure_same_passada_split_sets_already_split(
    tmp_path: Path,
) -> None:
    """Ticket 11 — numa passada única `run` (split→measure na mesma
    invocação), `measure` recebe `already_split=True`: `split` acabou de rodar
    e já emitiu os avisos de `in_values`/`outros` para o mesmo dataset."""
    request = _scaffold(tmp_path, csv_body=_GOOD_CSV)
    with patch(
        'pyauditor.orchestration.command_dispatch.run_measure',
        return_value=SimpleNamespace(status='done', error_message=None),
    ) as m:
        execute_run(request)

    assert m.call_args.kwargs['already_split'] is True
