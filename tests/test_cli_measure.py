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


def _write_config_and_data(
    config_dir: Path, data_dir: Path, csv_body: str
) -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    competencia_data_dir = data_dir / '2026' / '06'
    competencia_data_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / 'inms-test.yaml').write_text(CONFIG_YAML, encoding='utf-8')
    (competencia_data_dir / 'data.csv').write_text(csv_body, encoding='utf-8')


def test_measure_reads_data_from_competencia_subfolder(tmp_path: Path) -> None:
    """`measure 2026-06 --data-dir input` reads CSVs from `input/2026/06/` —
    a stray file at the data-dir root must be ignored."""
    config_dir = tmp_path / 'configs'
    data_dir = tmp_path / 'input'
    output_dir = tmp_path / 'roms'
    _write_config_and_data(
        config_dir,
        data_dir,
        'Nº Solicitacao;DataHoraFim;No prazo\n1;2026-06-01;S\n2;2026-06-02;N\n',
    )
    # Decoy at the data-dir root with the same name — shadows nothing, must be
    # ignored.
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / 'data.csv').write_text(
        'Nº Solicitacao;DataHoraFim;No prazo\n1;2026-06-01;S\n',
        encoding='utf-8',
    )

    exit_code = run_measure('2026-06', config_dir, data_dir, output_dir)

    rom_path = output_dir / '2026-06' / 'INMS-TEST.md'
    assert exit_code.status == 'done'
    content = rom_path.read_text(encoding='utf-8')
    assert '- Numerador: 1.0\n- Denominador: 2.0' in content

    # A different competência reads its own folder from the same data-dir.
    (data_dir / '2026' / '05').mkdir(parents=True, exist_ok=True)
    (data_dir / '2026' / '05' / 'data.csv').write_text(
        'Nº Solicitacao;DataHoraFim;No prazo\n1;2026-05-01;N\n2;2026-05-02;N\n',
        encoding='utf-8',
    )
    run_measure('2026-05', config_dir, data_dir, output_dir)
    rom_05 = (output_dir / '2026-05' / 'INMS-TEST.md').read_text(
        encoding='utf-8'
    )
    assert '- Denominador: 2.0' in rom_05


def test_measure_writes_one_rom_per_indicator_and_is_idempotent(
    tmp_path: Path,
) -> None:
    config_dir = tmp_path / 'configs'
    data_dir = tmp_path / 'input'
    output_dir = tmp_path / 'roms'
    _write_config_and_data(
        config_dir,
        data_dir,
        'Nº Solicitacao;DataHoraFim;No prazo\n1;2026-06-01;S\n2;2026-06-02;N\n',
    )

    exit_code = run_measure('2026-06', config_dir, data_dir, output_dir)

    rom_path = output_dir / '2026-06' / 'INMS-TEST.md'
    assert exit_code.status == 'done'
    assert rom_path.exists()
    first_write = rom_path.read_text(encoding='utf-8')

    # Rerun with different data — the ROM must reflect the new run, not
    # accumulate.
    _write_config_and_data(
        config_dir,
        data_dir,
        'Nº Solicitacao;DataHoraFim;No prazo\n1;2026-06-01;S\n',
    )
    run_measure('2026-06', config_dir, data_dir, output_dir)
    second_write = rom_path.read_text(encoding='utf-8')

    assert first_write != second_write
    assert 'Numerador: 1' in second_write
    assert 'Numerador: 1\n- Denominador: 2' not in second_write


def test_measure_exits_nonzero_on_hard_failure(tmp_path: Path) -> None:
    config_dir = tmp_path / 'configs'
    data_dir = tmp_path / 'input'
    output_dir = tmp_path / 'roms'
    # Every row fails the not_null(DataHoraFim) check -> zero accepted rows.
    _write_config_and_data(
        config_dir,
        data_dir,
        'Nº Solicitacao;DataHoraFim;No prazo\n1;;S\n2;;N\n',
    )

    exit_code = run_measure('2026-06', config_dir, data_dir, output_dir)

    assert exit_code.status == 'error'
    rom_path = output_dir / '2026-06' / 'INMS-TEST.md'
    assert rom_path.exists()  # ROM still written so rejections are visible


def test_measure_os_error_writing_rom_has_actionable_hint(
    tmp_path: Path,
) -> None:
    # Ticket 11: falha ao gravar o ROM (permissão/lock) ganha dica acionável.
    config_dir = tmp_path / 'configs'
    data_dir = tmp_path / 'input'
    output_dir = tmp_path / 'roms'
    _write_config_and_data(
        config_dir,
        data_dir,
        'Nº Solicitacao;DataHoraFim;No prazo\n1;2026-06-01;S\n2;2026-06-02;N\n',
    )

    with patch.object(
        Path, 'write_text', side_effect=PermissionError('Permission denied')
    ):
        exit_code = run_measure('2026-06', config_dir, data_dir, output_dir)

    assert exit_code.status == 'error'
    failing = next(i for i in exit_code.indicators if i.hard_failure)
    assert failing.error is not None
    assert 'aberto em outro programa' in failing.error


def test_measure_missing_dataset_is_not_activated_not_a_failure(
    tmp_path: Path,
) -> None:
    """Spec §14.1: um CSV ausente na competência não é falha de medição — o
    elemento contratual não foi demandado/ativado no período. `measure` deve
    completar com sucesso, emitir o WARNING e marcar o indicador como
    `not_activated`, sem escrever ROM/JSON para ele."""
    config_dir = tmp_path / 'configs'
    data_dir = tmp_path / 'input'
    output_dir = tmp_path / 'roms'
    config_dir.mkdir(parents=True)
    (data_dir / '2026' / '06').mkdir(parents=True)
    (config_dir / 'inms-test.yaml').write_text(
        CONFIG_YAML.replace('csv: data.csv', 'csv: missing.csv'),
        encoding='utf-8',
    )

    exit_code = run_measure('2026-06', config_dir, data_dir, output_dir)

    assert exit_code.status == 'done'
    outcome = exit_code.indicators[0]
    assert outcome.not_activated is True
    assert outcome.hard_failure is False
    assert not outcome.rom_path.exists()
    assert not outcome.summary_path.exists()
    assert any(
        'INMS TEST (MinC/2026-06): não ativado — dataset ausente '
        '(serviço não requisitado no período)' in warning
        for warning in exit_code.warnings
    )


def _write_per_orgao_config_and_data(
    tmp_path: Path, orgao: str, contract: str, csv_body: str
) -> None:
    config_dir = tmp_path / 'configs' / orgao
    data_dir = tmp_path / 'input' / orgao
    config_dir.mkdir(parents=True, exist_ok=True)
    month_dir = data_dir / '2026' / '06'
    month_dir.mkdir(parents=True, exist_ok=True)
    yaml = CONFIG_YAML
    if orgao != 'MinC':
        yaml = yaml.replace('orgao: MinC', f'orgao: {orgao}')
        yaml = yaml.replace('Ministério da Cultura', contract)
    (config_dir / 'inms-test.yaml').write_text(yaml, encoding='utf-8')
    (month_dir / 'data.csv').write_text(csv_body, encoding='utf-8')


def test_measure_both_writes_per_orgao_and_combined_roms(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    config_dir = tmp_path / 'configs'
    data_dir = tmp_path / 'input'
    output_dir = tmp_path / 'roms'
    _write_per_orgao_config_and_data(
        tmp_path,
        'MinC',
        'Ministério da Cultura',
        'Nº Solicitacao;DataHoraFim;No prazo\n1;2026-06-01;S\n2;2026-06-02;N\n',
    )
    _write_per_orgao_config_and_data(
        tmp_path,
        'MTur',
        'Ministério do Turismo',
        'Nº Solicitacao;DataHoraFim;No prazo\n1;2026-06-01;S\n',
    )

    code = cli_main(
        [
            'measure',
            '2026-06',
            '--orgao',
            'both',
            '--config-dir',
            str(config_dir),
            '--data-dir',
            str(data_dir),
            '--output-dir',
            str(output_dir),
        ]
    )

    assert code == 0
    per_minc = output_dir / 'MinC' / '2026-06' / 'INMS-TEST.md'
    per_mtur = output_dir / 'MTur' / '2026-06' / 'INMS-TEST.md'
    assert per_minc.exists()
    assert per_mtur.exists()

    combined = output_dir / 'both' / '2026-06' / 'INMS-TEST.md'
    assert combined.exists()
    combined_content = combined.read_text(encoding='utf-8')
    assert (
        '# ROM — INMS TEST (Indicador sintético) — MinC e MTur'
        in combined_content
    )
    assert combined_content.index('## MinC') < combined_content.index('## MTur')
    assert combined_content.count('### Resultado vs meta') == 2
    assert '- Órgão: MinC' in combined_content
    assert '- Órgão: MTur' in combined_content


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
    'Nº Solicitacao;DataHoraFim;No prazo;Grupo_executor\n'
    '1;2026-06-01;S;N1\n'
    '2;2026-06-02;S;N1\n'
    '3;2026-06-03;S;(CIT) - Infra\n'
)


def test_run_measure_ignores_split_derived_configs_on_disk(
    tmp_path: Path,
) -> None:
    """Regressão: `split` materializa `inms-01.<categoria>.yaml` no mesmo
    diretório do config base (ADR 0002). `run_measure` já expande as
    categorias em memória a partir do config base (Ticket 04) — se também
    redescobrir os YAMLs derivados pelo glob, reprocessa cada categoria de
    novo a partir do CSV já filtrado, produzindo ids compostos espúrios
    (`INMS-01.ATENDIMENTO_N1.ATENDIMENTO_N1` etc.)."""
    config_dir = tmp_path / 'configs'
    data_dir = tmp_path / 'input'
    output_dir = tmp_path / 'roms'
    competencia_data_dir = data_dir / '2026' / '06'
    competencia_data_dir.mkdir(parents=True)
    config_dir.mkdir(parents=True)
    (config_dir / 'inms-01.yaml').write_text(
        _CATEGORIA_CONFIG_YAML, encoding='utf-8'
    )
    (config_dir / 'categorias.yaml').write_text(
        _CATEGORIAS_YAML, encoding='utf-8'
    )
    (competencia_data_dir / 'inms-01.csv').write_text(
        _CATEGORIA_RAW_CSV, encoding='utf-8'
    )

    split_result = run_split(
        '2026-06', config_dir, data_dir, expected_orgao='MinC'
    )
    assert split_result.status == 'done'
    assert (config_dir / 'inms-01.ATENDIMENTO_N1.yaml').exists()
    assert (config_dir / 'inms-01.OPERACAO_N3.yaml').exists()

    result = run_measure(
        '2026-06', config_dir, data_dir, output_dir, expected_orgao='MinC'
    )

    assert result.status == 'done'
    assert len(result.indicators) == 2
    written = {p.stem for p in (output_dir / '2026-06').glob('*.md')}
    assert written == {'INMS-01.ATENDIMENTO_N1', 'INMS-01.OPERACAO_N3'}


def _write_categoria_fixture_with_empty_window(
    tmp_path: Path,
) -> tuple[Path, Path, Path]:
    config_dir = tmp_path / 'configs'
    data_dir = tmp_path / 'input'
    output_dir = tmp_path / 'roms'
    competencia_data_dir = data_dir / '2026' / '06'
    competencia_data_dir.mkdir(parents=True)
    config_dir.mkdir(parents=True)
    (config_dir / 'inms-01.yaml').write_text(
        _CATEGORIA_CONFIG_YAML, encoding='utf-8'
    )
    (config_dir / 'categorias.yaml').write_text(
        _CATEGORIAS_YAML, encoding='utf-8'
    )
    (competencia_data_dir / 'inms-01.csv').write_text(
        'Nº '
        'Solicitacao;DataHoraFim;No '
        'prazo;Grupo_executor\n1;20/05/2026 '
        '10:00;S;N1\n',
        encoding='utf-8',
    )
    return config_dir, data_dir, output_dir


def test_run_measure_categoria_warns_empty_window_when_standalone(
    tmp_path: Path,
) -> None:
    """Ticket 05 — o caminho em-memória (categorias) ganha o mesmo WARN de
    janela vazia que o caminho single já emitia; sem `already_split`
    (`pyauditor measure` isolado), o aviso deve aparecer."""
    import sys
    from datetime import date
    from io import StringIO

    from pyauditor.logging import setup_logging
    from pyauditor.periodo import PeriodoAfericao

    config_dir, data_dir, output_dir = (
        _write_categoria_fixture_with_empty_window(tmp_path)
    )
    periodo = PeriodoAfericao(date(2026, 6, 1), date(2026, 6, 30))
    buf = StringIO()
    setup_logging(sink=buf, level='INFO')

    try:
        result = run_measure(
            '2026-06',
            config_dir,
            data_dir,
            output_dir,
            expected_orgao='MinC',
            periodo=periodo,
        )
    finally:
        setup_logging(sink=sys.stderr, level='INFO')

    assert result.status == 'done'
    assert 'nenhuma linha no período' in buf.getvalue()


def test_run_measure_categoria_already_split_suppresses_duplicate_warn(
    tmp_path: Path,
) -> None:
    """`already_split=True` (dispatch de `run`) suprime o WARN/INFO — `split`
    já os logou para o mesmo dataset bruto na mesma passada."""
    import sys
    from datetime import date
    from io import StringIO

    from pyauditor.logging import setup_logging
    from pyauditor.periodo import PeriodoAfericao

    config_dir, data_dir, output_dir = (
        _write_categoria_fixture_with_empty_window(tmp_path)
    )
    periodo = PeriodoAfericao(date(2026, 6, 1), date(2026, 6, 30))
    buf = StringIO()
    setup_logging(sink=buf, level='INFO')

    try:
        result = run_measure(
            '2026-06',
            config_dir,
            data_dir,
            output_dir,
            expected_orgao='MinC',
            periodo=periodo,
            already_split=True,
        )
    finally:
        setup_logging(sink=sys.stderr, level='INFO')

    assert result.status == 'done'
    assert 'nenhuma linha no período' not in buf.getvalue()


def test_run_measure_already_split_dedups_in_values_e_outros_warning(
    tmp_path: Path,
) -> None:
    """Ticket 11 — quando `run` roda split+measure na mesma passada, os avisos
    de `in_values` sem correspondência e de `outros` saem 1x por passada:
    `split` já os emitiu sobre os mesmos `real_values`, `run_measure`
    (`already_split=True`) não duplica."""
    import sys
    from datetime import date
    from io import StringIO

    from pyauditor.logging import setup_logging
    from pyauditor.periodo import PeriodoAfericao

    config_dir, data_dir, output_dir = (
        _write_categoria_fixture_with_empty_window(tmp_path)
    )
    # in_values N1 existe no dataset; "outros" não se aplica — usa um in_values
    # órfão para forçar o aviso de sem-correspondência nos dois caminhos.
    csv_path = data_dir / '2026' / '06' / 'inms-01.csv'
    csv_path.write_text(
        'Nº Solicitacao;DataHoraFim;No prazo;Grupo_executor\n'
        '1;2026-06-01;S;N0\n',
        encoding='utf-8',
    )
    periodo = PeriodoAfericao(date(2026, 6, 1), date(2026, 6, 30))
    buf = StringIO()
    setup_logging(sink=buf, level='INFO')

    try:
        split_result = run_split(
            '2026-06',
            config_dir,
            data_dir,
            expected_orgao='MinC',
            periodo=periodo,
        )
        measure_result = run_measure(
            '2026-06',
            config_dir,
            data_dir,
            output_dir,
            expected_orgao='MinC',
            periodo=periodo,
            already_split=True,
        )
    finally:
        setup_logging(sink=sys.stderr, level='INFO')

    output = buf.getvalue()
    assert split_result.status == 'done'
    assert measure_result.status == 'done'
    said = output.count('sem correspondência')
    assert said == 1  # split emitiu; measure (already_split) não duplica


def _write_whole_indicator_empty_window(
    tmp_path: Path,
) -> tuple[Path, Path, Path]:
    config_dir = tmp_path / 'configs'
    data_dir = tmp_path / 'input'
    output_dir = tmp_path / 'roms'
    _write_config_and_data(
        config_dir,
        data_dir,
        'Nº Solicitacao;DataHoraFim;No prazo\n1;20/05/2026 10:00;S\n',
    )
    return config_dir, data_dir, output_dir


def test_run_measure_single_path_warns_empty_window_when_standalone(
    tmp_path: Path,
) -> None:
    """Ticket 05 — o caminho single (whole_indicator) mantém o WARN de janela
    vazia no `pyauditor measure` isolado (`already_split=False`)."""
    import sys
    from datetime import date
    from io import StringIO

    from pyauditor.logging import setup_logging
    from pyauditor.periodo import PeriodoAfericao

    config_dir, data_dir, output_dir = _write_whole_indicator_empty_window(
        tmp_path
    )
    periodo = PeriodoAfericao(date(2026, 6, 1), date(2026, 6, 30))
    buf = StringIO()
    setup_logging(sink=buf, level='INFO')

    try:
        result = run_measure(
            '2026-06',
            config_dir,
            data_dir,
            output_dir,
            expected_orgao='MinC',
            periodo=periodo,
        )
    finally:
        setup_logging(sink=sys.stderr, level='INFO')

    assert result.status == 'done'
    assert 'nenhuma linha no período' in buf.getvalue()


def test_run_measure_single_path_suppresses_empty_window_warn_when_already_split(  # noqa: E501
    tmp_path: Path,
) -> None:
    """Ticket 05 — `already_split=True` (dispatch de `run`) também suprime o
    WARN de janela vazia do caminho single (whole_indicator): `split` já o
    logou para o mesmo dataset bruto na mesma passada."""
    import sys
    from datetime import date
    from io import StringIO

    from pyauditor.logging import setup_logging
    from pyauditor.periodo import PeriodoAfericao

    config_dir, data_dir, output_dir = _write_whole_indicator_empty_window(
        tmp_path
    )
    periodo = PeriodoAfericao(date(2026, 6, 1), date(2026, 6, 30))
    buf = StringIO()
    setup_logging(sink=buf, level='INFO')

    try:
        result = run_measure(
            '2026-06',
            config_dir,
            data_dir,
            output_dir,
            expected_orgao='MinC',
            periodo=periodo,
            already_split=True,
        )
    finally:
        setup_logging(sink=sys.stderr, level='INFO')

    assert result.status == 'done'
    assert 'nenhuma linha no período' not in buf.getvalue()


def _write_categoria_fixture(config_dir: Path, data_dir: Path) -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    competencia_data_dir = data_dir / '2026' / '06'
    competencia_data_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / 'inms-01.yaml').write_text(
        _CATEGORIA_CONFIG_YAML, encoding='utf-8'
    )
    (config_dir / 'categorias.yaml').write_text(
        _CATEGORIAS_YAML, encoding='utf-8'
    )


def test_run_measure_categoria_missing_dataset_marks_not_activated(
    tmp_path: Path,
) -> None:
    """Ramo categoria expandido em memória: `measurement_source` levanta
    `FileNotFoundError` (dataset ausente) — não é falha; cada categoria vira
    `not_activated`, sem ROM/JSON."""
    config_dir = tmp_path / 'configs'
    data_dir = tmp_path / 'input'
    output_dir = tmp_path / 'roms'
    _write_categoria_fixture(config_dir, data_dir)
    # Nenhum CSV referenciado (inms-01.csv) é gravado.

    result = run_measure(
        '2026-06', config_dir, data_dir, output_dir, expected_orgao='MinC'
    )

    assert result.status == 'done'
    assert len(result.indicators) == 2
    assert all(
        o.not_activated and not o.hard_failure for o in result.indicators
    )
    assert all(not o.rom_path.exists() for o in result.indicators)


def test_run_measure_categoria_exception_hard_fails_all(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ramo categoria: `measurement_source` levanta `OSError`/`ValueError` (ex.:
    coluna requerida ausente no CSV) — falha técnica do dataset bruto; todas as
    categorias derivadas são marcadas hard-failure com a mesma mensagem."""
    config_dir = tmp_path / 'configs'
    data_dir = tmp_path / 'input'
    output_dir = tmp_path / 'roms'
    _write_categoria_fixture(config_dir, data_dir)
    competencia_data_dir = data_dir / '2026' / '06'
    # Sem a coluna "No prazo" referenciada no YAML → _validate_columns levanta
    # ValueError dentro do backbone.
    (competencia_data_dir / 'inms-01.csv').write_text(
        'Nº Solicitacao;DataHoraFim;Grupo_executor\n1;2026-06-01;N1\n',
        encoding='utf-8',
    )

    result = run_measure(
        '2026-06', config_dir, data_dir, output_dir, expected_orgao='MinC'
    )

    assert result.status == 'error'
    assert len(result.indicators) == 2
    assert all(o.hard_failure for o in result.indicators)
    assert all(o.error is not None for o in result.indicators)


def test_run_measure_categoria_missing_grupo_executor_column(
    tmp_path: Path,
) -> None:
    """Ramo categoria: CSV sem a coluna `Grupo_executor` — mensagem específica
    de configuração errada (mode: grupo_executor sem a coluna)."""
    config_dir = tmp_path / 'configs'
    data_dir = tmp_path / 'input'
    output_dir = tmp_path / 'roms'
    _write_categoria_fixture(config_dir, data_dir)
    competencia_data_dir = data_dir / '2026' / '06'
    (competencia_data_dir / 'inms-01.csv').write_text(
        'Nº Solicitacao;DataHoraFim;No prazo\n1;2026-06-01;S\n',
        encoding='utf-8',
    )

    result = run_measure(
        '2026-06', config_dir, data_dir, output_dir, expected_orgao='MinC'
    )

    assert result.status == 'error'
    assert any(
        "não tem coluna 'Grupo_executor'" in (o.error or '')
        for o in result.indicators
    )


def test_run_measure_categoria_partial_match_warns_valores_nao_encontrados(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ramo 470-475: `in_values` com correspondência parcial — alguns literais
    existem no CSV, outros não; o aviso é "valores não encontrados no CSV"
    (não o de typo/categoria sem linhas)."""
    config_dir = tmp_path / 'configs'
    data_dir = tmp_path / 'input'
    output_dir = tmp_path / 'roms'
    config_dir.mkdir(parents=True, exist_ok=True)
    competencia_data_dir = data_dir / '2026' / '06'
    competencia_data_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / 'inms-01.yaml').write_text(
        _CATEGORIA_CONFIG_YAML, encoding='utf-8'
    )
    (config_dir / 'categorias.yaml').write_text(
        """\
categorias:
  ATENDIMENTO_N1:
    label: "Atendimento Remoto"
    inms:
      "1.1": {mode: grupo_executor, in_values: ["N1", "N0"]}
""",
        encoding='utf-8',
    )
    # N1 presente; N0 ausente → correspondência parcial.
    (competencia_data_dir / 'inms-01.csv').write_text(
        'Nº Solicitacao;DataHoraFim;No prazo;Grupo_executor\n'
        '1;2026-06-01;S;N1\n',
        encoding='utf-8',
    )

    result = run_measure(
        '2026-06', config_dir, data_dir, output_dir, expected_orgao='MinC'
    )

    assert result.status == 'done'
    assert any(
        "['N0'] sem correspondência — valores não encontrados no CSV" in w
        for w in result.warnings
    )


def test_run_measure_categoria_strategy_exception_is_hard_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ramo 520-533: exceção dentro da medição por categoria (QualityGateRunner
    falha) — categoria específica vira hard_failure sem derrubar o run."""
    from pyauditor.cli import measure as measure_module

    config_dir = tmp_path / 'configs'
    data_dir = tmp_path / 'input'
    output_dir = tmp_path / 'roms'
    _write_categoria_fixture(config_dir, data_dir)
    competencia_data_dir = data_dir / '2026' / '06'
    (competencia_data_dir / 'inms-01.csv').write_text(
        _CATEGORIA_RAW_CSV, encoding='utf-8'
    )
    monkeypatch.setattr(
        measure_module,
        'QualityGateRunner',
        _FailingQualityGateRunner,
    )

    result = run_measure(
        '2026-06', config_dir, data_dir, output_dir, expected_orgao='MinC'
    )

    assert result.status == 'error'
    assert any(o.hard_failure for o in result.indicators)


class _FailingQualityGateRunner:
    """Stub que derruba na execução para cobrir o ramo de exceção por
    categoria."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        pass

    def run(self, rows: object) -> object:
        raise RuntimeError('boom na medição')


def test_run_measure_categoria_outros_warns_when_standalone(
    tmp_path: Path,
) -> None:
    """Ramo 548-554: `measure` isolado (already_split=False) emite o warning de
    linhas `outros` que `split` emeteria no seu caminho — mesma regra."""
    import sys
    from io import StringIO

    from pyauditor.logging import setup_logging

    config_dir = tmp_path / 'configs'
    data_dir = tmp_path / 'input'
    output_dir = tmp_path / 'roms'
    config_dir.mkdir(parents=True, exist_ok=True)
    competencia_data_dir = data_dir / '2026' / '06'
    competencia_data_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / 'inms-01.yaml').write_text(
        _CATEGORIA_CONFIG_YAML, encoding='utf-8'
    )
    (config_dir / 'categorias.yaml').write_text(
        _CATEGORIAS_YAML, encoding='utf-8'
    )
    # Linha "Grupo Desconhecido" não pertence a N1 nem a (CIT) → vai p/ outros.
    (competencia_data_dir / 'inms-01.csv').write_text(
        'Nº Solicitacao;DataHoraFim;No prazo;Grupo_executor\n'
        '1;2026-06-01;S;N1\n'
        '2;2026-06-02;S;(CIT) - Infra\n'
        '3;2026-06-03;S;Grupo Desconhecido\n',
        encoding='utf-8',
    )
    buf = StringIO()
    setup_logging(sink=buf, level='INFO')

    try:
        result = run_measure(
            '2026-06', config_dir, data_dir, output_dir, expected_orgao='MinC'
        )
    finally:
        setup_logging(sink=sys.stderr, level='INFO')

    assert result.status == 'done'
    assert any(
        'categoria outros: 1 linha(s) não classificada(s) em nenhuma categoria'
        in w
        for w in result.warnings
    )


def test_check_measure_ready_always_satisfied() -> None:
    from pyauditor.cli.measure import check_measure_ready

    assert check_measure_ready().satisfied is True


def test_run_measure_invalid_competencia_is_error(tmp_path: Path) -> None:
    config_dir = tmp_path / 'configs'
    data_dir = tmp_path / 'input'
    output_dir = tmp_path / 'roms'
    config_dir.mkdir(parents=True)

    result = run_measure('2026/06', config_dir, data_dir, output_dir)

    assert result.status == 'error'
    assert result.error_message is not None
    assert 'competência inválida' in result.error_message


def test_run_measure_typo_indicator_key_is_error(tmp_path: Path) -> None:
    """Config com chave 'indicador:' (typo) → `discover_config_files` levanta
    ValueError; `run_measure` vira erro com mensagem acionável."""
    config_dir = tmp_path / 'configs'
    data_dir = tmp_path / 'input'
    output_dir = tmp_path / 'roms'
    config_dir.mkdir(parents=True)
    (config_dir / 'inms-test.yaml').write_text(
        'indicador:\n  id: INMS-TEST\n', encoding='utf-8'
    )

    result = run_measure('2026-06', config_dir, data_dir, output_dir)

    assert result.status == 'error'
    assert 'falha ao carregar configs' in (result.error_message or '')
    assert result.indicators == ()


def test_run_measure_no_configs_found_is_error(tmp_path: Path) -> None:
    config_dir = tmp_path / 'configs'
    data_dir = tmp_path / 'input'
    output_dir = tmp_path / 'roms'
    config_dir.mkdir(parents=True)
    (config_dir / 'datasets.yaml').write_text(
        'manifests: []\n', encoding='utf-8'
    )

    result = run_measure('2026-06', config_dir, data_dir, output_dir)

    assert result.status == 'error'
    assert 'nenhum config encontrado' in (result.error_message or '')


def test_run_measure_mkdir_failure_is_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_dir, data_dir, output_dir = _write_whole_indicator_empty_window(
        tmp_path
    )
    malformed_output = tmp_path / 'roms' / '2026-06'
    (tmp_path / 'roms').mkdir(parents=True)
    malformed_output.write_text('bloqueia como arquivo', encoding='utf-8')

    result = run_measure('2026-06', config_dir, data_dir, tmp_path / 'roms')

    assert result.status == 'error'
    assert 'falha ao criar diretório' in (result.error_message or '')


def test_run_measure_single_path_measure_error_is_hard_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Caminho single: exceção arbitrária dentro de `measure` vira hard-failure
    do indicador, sem derrubar o comando."""
    from pyauditor.cli import measure as measure_module
    from pyauditor.config.models import IndicatorConfig

    config_dir, data_dir, output_dir = _write_whole_indicator_empty_window(
        tmp_path
    )

    def _boom(
        config: IndicatorConfig,
        data_dir: Path,
        **kwargs: object,
    ) -> object:
        raise RuntimeError('engine derrubou')

    monkeypatch.setattr(measure_module, 'measure', _boom)

    result = run_measure(
        '2026-06', config_dir, data_dir, output_dir, expected_orgao='MinC'
    )

    assert result.status == 'error'
    assert len(result.indicators) == 1
    assert result.indicators[0].hard_failure
    assert 'exceção na medição' in (result.indicators[0].error or '')


def test_write_combined_roms_skips_indicator_with_single_orgao(
    tmp_path: Path,
) -> None:
    """`write_combined_roms` só renderiza o combinado quando os dois órgãos
    mediram o indicador — órfão de um lado → warning e nenhum arquivo."""
    import sys
    from io import StringIO

    from pyauditor.cli.measure import _MeasuredIndicator, write_combined_roms
    from pyauditor.logging import setup_logging

    config_dir, data_dir, output_dir = _write_whole_indicator_empty_window(
        tmp_path
    )
    collected: list[_MeasuredIndicator] = []
    result = run_measure(
        '2026-06',
        config_dir,
        data_dir,
        output_dir,
        expected_orgao='MinC',
        collect=collected,
    )

    assert result.status == 'done'
    assert len(collected) == 1

    # Só o órgão MinC mediu — nenhum par para combinar.
    buf = StringIO()
    setup_logging(sink=buf, level='WARNING')
    try:
        write_combined_roms({'MinC': collected}, '2026-06', output_dir)
    finally:
        setup_logging(sink=sys.stderr, level='INFO')

    assert 'falta medição de' in buf.getvalue()
    assert list((output_dir / 'both' / '2026-06').glob('*.md')) == []


def test_run_measure_categorias_fallback_parent_orgao_dir(
    tmp_path: Path,
) -> None:
    """Config_dir `_shared` sem categorias.yaml: fallback para
    `<parent>/<orgao>/categorias.yaml` (single-source por órgão) — o mesmo
    caminho que `split` usa; medida expande em categoria."""
    configs = tmp_path / 'configs'
    (configs / '_shared').mkdir(parents=True)
    data_dir = tmp_path / 'input'
    output_dir = tmp_path / 'roms'
    (configs / '_shared' / 'inms-01.yaml').write_text(
        _CATEGORIA_CONFIG_YAML, encoding='utf-8'
    )
    (configs / 'MinC').mkdir(parents=True)
    (configs / 'MinC' / 'categorias.yaml').write_text(
        _CATEGORIAS_YAML, encoding='utf-8'
    )
    competencia_data_dir = data_dir / '2026' / '06'
    competencia_data_dir.mkdir(parents=True)
    (competencia_data_dir / 'inms-01.csv').write_text(
        _CATEGORIA_RAW_CSV, encoding='utf-8'
    )

    result = run_measure(
        '2026-06',
        configs / '_shared',
        data_dir,
        output_dir,
        expected_orgao='MinC',
    )

    assert result.status == 'done'
    assert len(result.indicators) == 2
