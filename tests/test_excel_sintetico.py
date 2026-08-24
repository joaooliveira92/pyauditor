from pathlib import Path

import pytest
from openpyxl import load_workbook

from pyauditor.config.categorias import load_categorias
from pyauditor.excel.sintetico import write_sintetico_workbook

_INMS_01_CONFIG = """\
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

_INMS_09_CONFIG = """\
indicator:
  id: INMS-09
  contractual_id: "INMS 1.9"
  name: Mudanças atendidas dentro do prazo

scope:
  contract: "40/2022 - Ministério da Cultura"
  orgao: MinC

source:
  csv: inms-09.csv
  delimiter: ";"
  encoding: utf-8

quality_gates:
  checks: []

calculation:
  shape: ratio
  aggregation: count_distinct
  numerator_filter:
    column: "Situação"
    equals: "No prazo"

target:
  operator: ">="
  value: 95.0

penalty:
  base_points: 100
  step_points: 10
  step_size_pct: 1.0
"""

_INMS_04_CONFIG = """\
indicator:
  id: INMS-04
  contractual_id: "INMS 1.4"
  name: Disponibilidade de sistema crítico

scope:
  contract: "40/2022 - Ministério da Cultura"
  orgao: MinC

source:
  csv: inms-04.csv
  delimiter: ";"
  encoding: utf-8

quality_gates:
  checks: []

calculation:
  shape: ratio
  aggregation: count_distinct
  numerator_filter:
    column: "Situação"
    equals: "Disponível"

target:
  operator: ">="
  value: 99.0

penalty:
  base_points: 100
  step_points: 10
  step_size_pct: 1.0
"""

_INMS_14_CONFIG = """\
indicator:
  id: INMS-14
  contractual_id: "INMS 1.14"
  name: Índice de disponibilidade de serviços de infraestrutura

scope:
  contract: "40/2022 - Ministério da Cultura"
  orgao: MinC

source:
  csv: inms-14.csv
  delimiter: ";"
  encoding: utf-8

quality_gates:
  checks: []

calculation:
  shape: precomputed_table
  result_column: inms_1_14_percentual
  name_column: servico_infraestrutura
  numerator_column: numerador_inms_horas
  denominator_column: base_apuracao_horas
  penalty_column: penalidade_pontos

target:
  operator: ">="
  value: 99.5
"""

_CATEGORIAS_YAML = """\
categorias:
  ATENDIMENTO_N1:
    label: "Atendimento Remoto aos Usuários"
    inms:
      "1.1": {mode: grupo_executor, in_values: ["N1"]}
  ATENDIMENTO_N2:
    label: "Atendimento Presencial aos Usuários"
    inms:
      "1.1": {mode: grupo_executor, in_values: ["N2"]}
  OPERACAO_N3:
    label: "Operação e Sustentação da Infraestrutura de TI"
    inms:
      "1.1": {mode: grupo_executor, catch_all_contains: "(CIT)"}
      "1.9": {mode: whole_indicator}
  MONITORAMENTO_NOC_SOC:
    label: "Monitoramento de Ambiente (NOC/SOC)"
    inms:
      "1.4": {mode: whole_indicator}
"""

_CATEGORIAS_YAML_COM_1_14 = """\
categorias:
  ATENDIMENTO_N1:
    label: "Atendimento Remoto aos Usuários"
    inms:
      "1.1": {mode: grupo_executor, in_values: ["N1"]}
  ATENDIMENTO_N2:
    label: "Atendimento Presencial aos Usuários"
    inms:
      "1.1": {mode: grupo_executor, in_values: ["N2"]}
  OPERACAO_N3:
    label: "Operação e Sustentação da Infraestrutura de TI"
    inms:
      "1.1": {mode: grupo_executor, catch_all_contains: "(CIT)"}
      "1.9": {mode: whole_indicator}
      "1.14": {mode: whole_indicator}
  MONITORAMENTO_NOC_SOC:
    label: "Monitoramento de Ambiente (NOC/SOC)"
    inms:
      "1.4": {mode: whole_indicator}
      "1.14": {mode: whole_indicator}
"""

# Nº Solicitacao;DataHoraSolicitacao;DataHoraFim;No prazo;Grupo_executor
# 1 (N1, S, 2h) / 2 (N1, N, 24h) / 3 (N2, S, 1h) / 4 ((CIT) - Infra, S, 12h) /
# 5 (Grupo Desconhecido, N, sem DataHoraFim -> rejeitada pelo quality gate).
_INMS_01_RAW_CSV = (
    'Nº Solicitacao;DataHoraSolicitacao;DataHoraFim;No prazo;Grupo_executor\n'
    '1;01/06/2026 08:00;01/06/2026 10:00;S;N1\n'
    '2;01/06/2026 09:00;02/06/2026 09:00;N;N1\n'
    '3;01/06/2026 08:00;01/06/2026 09:00;S;N2\n'
    '4;01/06/2026 08:00;01/06/2026 20:00;S;(CIT) - Infra\n'
    '5;01/06/2026 08:00;;N;Grupo Desconhecido\n'
)

_INMS_09_RAW_CSV = 'Chamado;Situação\n1;No prazo\n2;No prazo\n3;Fora do prazo\n'

# Anexo D, Tabela 28: 6 ativos nomeados, um por linha — mesmo formato do
# /input real (`disponibilidade_infra`), sem colunas de fila de atendimento
# (`No prazo`/`DataHoraSolicitacao`/`DataHoraFim`), que degradam pra "—".
_INMS_14_RAW_CSV = (
    'servico_infraestrutura;numerador_inms_horas;base_apuracao_horas;'
    'inms_1_14_percentual;penalidade_pontos\n'
    'File Server;715;720;99,3;250\n'
    'Telefonia;720;720;100,0;0\n'
    'Mensageria;720;720;100,0;0\n'
    'Servidores de impressão;720;720;100,0;0\n'
    'WI-FI;718;720;99,7;0\n'
    'Rede;720;720;100,0;0\n'
)


def _write_fixture(
    tmp_path: Path, *, include_inms_04_csv: bool, include_inms_14: bool = False
) -> tuple[Path, Path]:
    config_dir = tmp_path / 'configs'
    data_dir = tmp_path / 'input' / '2026' / '06'
    config_dir.mkdir(parents=True)
    data_dir.mkdir(parents=True)

    (config_dir / 'inms-01.yaml').write_text(_INMS_01_CONFIG, encoding='utf-8')
    (config_dir / 'inms-09.yaml').write_text(_INMS_09_CONFIG, encoding='utf-8')
    (config_dir / 'inms-04.yaml').write_text(_INMS_04_CONFIG, encoding='utf-8')
    categorias_yaml = (
        _CATEGORIAS_YAML_COM_1_14 if include_inms_14 else _CATEGORIAS_YAML
    )
    (config_dir / 'categorias.yaml').write_text(
        categorias_yaml, encoding='utf-8'
    )

    (data_dir / 'inms-01.csv').write_text(_INMS_01_RAW_CSV, encoding='utf-8')
    (data_dir / 'inms-09.csv').write_text(_INMS_09_RAW_CSV, encoding='utf-8')
    if include_inms_04_csv:
        (data_dir / 'inms-04.csv').write_text(
            'Situação\nDisponível\n', encoding='utf-8'
        )
    if include_inms_14:
        (config_dir / 'inms-14.yaml').write_text(
            _INMS_14_CONFIG, encoding='utf-8'
        )
        (data_dir / 'inms-14.csv').write_text(
            _INMS_14_RAW_CSV, encoding='utf-8'
        )

    return config_dir, data_dir


def test_sheet_names_cover_every_inms_with_categoria_entry(
    tmp_path: Path,
) -> None:
    config_dir, data_dir = _write_fixture(tmp_path, include_inms_04_csv=True)
    categorias_file = load_categorias(config_dir / 'categorias.yaml')
    output_path = tmp_path / 'sintetico.xlsx'

    warnings = write_sintetico_workbook(
        categorias_file, config_dir, data_dir, output_path
    )

    assert warnings == []
    wb = load_workbook(output_path)
    assert set(wb.sheetnames) == {
        'INMS 1.1',
        'INMS 1.9',
        'INMS 1.4',
        'Sansões',
    }


def test_grupo_executor_sheet_has_one_row_per_categoria_x_grupo_executor(
    tmp_path: Path,
) -> None:
    config_dir, data_dir = _write_fixture(tmp_path, include_inms_04_csv=True)
    categorias_file = load_categorias(config_dir / 'categorias.yaml')
    output_path = tmp_path / 'sintetico.xlsx'

    write_sintetico_workbook(categorias_file, config_dir, data_dir, output_path)

    wb = load_workbook(output_path)
    sheet = wb['INMS 1.1']
    assert tuple(cell.value for cell in sheet[1]) == (
        'Categoria',
        'Nível',
        'Grupo executor',
        'Linhas',
        'Dentro do prazo',
        'Fora do prazo',
        '% bruto',
        'Tempo médio criação→resolução',
    )

    rows_by_grupo = {
        row[2].value: row for row in sheet.iter_rows(min_row=2, max_row=5)
    }

    n1_row = rows_by_grupo['N1']
    assert [c.value for c in n1_row] == [
        'Atendimento Remoto aos Usuários',
        'N1',
        'N1',
        2,
        1,
        1,
        '50,0%',
        '0d 13h',
    ]

    n2_row = rows_by_grupo['N2']
    assert [c.value for c in n2_row] == [
        'Atendimento Presencial aos Usuários',
        'N2',
        'N2',
        1,
        1,
        0,
        '100,0%',
        '0d 01h',
    ]

    n3_row = rows_by_grupo['(CIT) - Infra']
    assert [c.value for c in n3_row] == [
        'Operação e Sustentação da Infraestrutura de TI',
        'N3',
        '(CIT) - Infra',
        1,
        1,
        0,
        '100,0%',
        '0d 12h',
    ]

    outros_row = rows_by_grupo['Grupo Desconhecido']
    assert [c.value for c in outros_row] == [
        'outros (não contabilizado na meta)',
        None,
        'Grupo Desconhecido',
        1,
        0,
        1,
        '0,0%',
        '—',
    ]


def test_grupo_executor_sheet_has_subtotals_by_nivel(tmp_path: Path) -> None:
    config_dir, data_dir = _write_fixture(tmp_path, include_inms_04_csv=True)
    categorias_file = load_categorias(config_dir / 'categorias.yaml')
    output_path = tmp_path / 'sintetico.xlsx'

    write_sintetico_workbook(categorias_file, config_dir, data_dir, output_path)

    wb = load_workbook(output_path)
    sheet = wb['INMS 1.1']
    header_row = next(
        row[0].row
        for row in sheet.iter_rows(min_row=1)
        if row[0].value == 'Subtotais por Nível'
    )
    assert header_row is not None
    subtotal_rows = {
        row[0].value: row[:6]
        for row in sheet.iter_rows(
            min_row=header_row + 2, max_row=header_row + 4
        )
    }

    assert [c.value for c in subtotal_rows['N1']] == [
        'N1',
        2,
        1,
        1,
        '50,0%',
        '0d 13h',
    ]
    assert [c.value for c in subtotal_rows['N2']] == [
        'N2',
        1,
        1,
        0,
        '100,0%',
        '0d 01h',
    ]
    assert [c.value for c in subtotal_rows['N3']] == [
        'N3',
        1,
        1,
        0,
        '100,0%',
        '0d 12h',
    ]


def test_whole_indicator_sheet_is_single_row_no_subtotals(
    tmp_path: Path,
) -> None:
    config_dir, data_dir = _write_fixture(tmp_path, include_inms_04_csv=True)
    categorias_file = load_categorias(config_dir / 'categorias.yaml')
    output_path = tmp_path / 'sintetico.xlsx'

    write_sintetico_workbook(categorias_file, config_dir, data_dir, output_path)

    wb = load_workbook(output_path)
    sheet = wb['INMS 1.9']
    data_rows = list(sheet.iter_rows(min_row=2))
    assert len(data_rows) == 1
    assert [c.value for c in data_rows[0]] == [
        'Operação e Sustentação da Infraestrutura de TI',
        'N3',
        '(indicador inteiro)',
        3,
        '—',
        '—',
        '—',
        '—',
    ]
    assert not any(
        cell.value == 'Subtotais por Nível'
        for row in sheet.iter_rows()
        for cell in row
    )


def test_inms_1_14_sheet_uses_enriched_precomputed_audit_renderer(
    tmp_path: Path,
) -> None:
    """INMS 1.14 tem o mesmo shape `precomputed_table`/`name_column` que
    1.4/1.5 (dataset `disponibilidade_infra`, um serviço por linha) — usa o
    mesmo renderer enriquecido, uma vez por categoria à qual pertence
    (produto cartesiano: 2 categorias x 6 serviços = 12 linhas), em vez do
    renderer de fila de atendimento (que não tem `No prazo` neste CSV e só
    produzia traços)."""
    config_dir, data_dir = _write_fixture(
        tmp_path, include_inms_04_csv=True, include_inms_14=True
    )
    categorias_file = load_categorias(config_dir / 'categorias.yaml')
    output_path = tmp_path / 'sintetico.xlsx'

    warnings = write_sintetico_workbook(
        categorias_file, config_dir, data_dir, output_path
    )

    assert warnings == []
    wb = load_workbook(output_path)
    assert 'INMS 1.14' in wb.sheetnames
    sheet = wb['INMS 1.14']

    assert 'Disponibilidade de sistema' in sheet['A1'].value

    headers = [cell.value for cell in sheet[16]]
    assert headers[:8] == [
        'Categoria',
        'Sistema / Serviço',
        'Resultado',
        'Meta',
        'Desvio vs Meta',
        'Faixas 0,1%',
        'Penalidade',
        'Meta atingida?',
    ]

    data_rows = list(sheet.iter_rows(min_row=17, max_row=28))
    assert len(data_rows) == 12

    operacao_n3_rows = [row[1].value for row in data_rows[:6]]
    noc_soc_rows = [row[1].value for row in data_rows[6:]]
    assert (
        operacao_n3_rows
        == noc_soc_rows
        == [
            'File Server',
            'Telefonia',
            'Mensageria',
            'Servidores de impressão',
            'WI-FI',
            'Rede',
        ]
    )

    # File Server (99,3 %) não atinge a meta (99,5 %) — penalidade do CSV.
    file_server = [c.value for c in data_rows[0]]
    assert file_server[0] == 'Operação e Sustentação da Infraestrutura de TI'
    assert file_server[2] == pytest.approx(0.993)
    assert file_server[6] == 250
    assert file_server[7] == 'Não'

    # WI-FI (99,7 %) atinge a meta.
    wifi = [c.value for c in data_rows[4]]
    assert wifi[2] == pytest.approx(0.997)
    assert wifi[7] == 'Sim'

    assert sheet['A32'].value.startswith('File Server')


def test_nao_ativado_when_raw_csv_missing(tmp_path: Path) -> None:
    config_dir, data_dir = _write_fixture(tmp_path, include_inms_04_csv=False)
    categorias_file = load_categorias(config_dir / 'categorias.yaml')
    output_path = tmp_path / 'sintetico.xlsx'

    warnings = write_sintetico_workbook(
        categorias_file, config_dir, data_dir, output_path
    )

    assert warnings == []
    wb = load_workbook(output_path)
    sheet = wb['INMS 1.4']
    assert sheet.cell(row=2, column=1).value == (
        'Esse serviço não foi requisitado no período selecionado.'
    )


def test_periodo_filtra_antes_dos_gates_e_falha_sem_period_column(
    tmp_path: Path,
) -> None:
    """Spec competencia-cli-equipe §2/§ issue 01 item 5 — sintetico aplica a
    mesma janela do split: linha de maio some das contagens; config sem
    `period_column` é erro acionável, aba daquele INMS é pulada (mesmo
    tratamento dos demais erros do loop) em vez do workbook inteiro cair."""
    from datetime import date

    from pyauditor.periodo import PeriodoAfericao

    config_dir, data_dir = _write_fixture(tmp_path, include_inms_04_csv=True)
    (data_dir / 'inms-01.csv').write_text(
        'Nº Solicitacao;DataHoraSolicitacao;DataHoraFim;No '
        'prazo;Grupo_executor\n'
        '1;01/06/2026 08:00;01/06/2026 10:00;S;N1\n'
        '2;20/05/2026 09:00;20/05/2026 11:00;N;N1\n'
        '3;02/06/2026 08:00;02/06/2026 09:00;S;N2\n',
        encoding='utf-8',
    )
    categorias_file = load_categorias(config_dir / 'categorias.yaml')
    output_path = tmp_path / 'sintetico.xlsx'

    warnings = write_sintetico_workbook(
        categorias_file,
        config_dir,
        data_dir,
        output_path,
        periodo=PeriodoAfericao(date(2026, 6, 1), date(2026, 6, 30)),
    )

    # INMS 1.9/1.4 não declaram period_column → erro acionável, aba pulada.
    assert any(
        'INMS 1.9' in w and 'period_column' in w and 'não declarado' in w
        for w in warnings
    )
    wb = load_workbook(output_path)
    assert 'INMS 1.9' not in wb.sheetnames
    assert 'INMS 1.4' not in wb.sheetnames
    sheet = wb['INMS 1.1']
    rows_by_grupo = {row[2].value: row for row in sheet.iter_rows(min_row=2)}
    n1 = [c.value for c in rows_by_grupo['N1']]
    assert n1[3:6] == [1, 1, 0]  # linha de maio descartada antes da segregação
    n2 = [c.value for c in rows_by_grupo['N2']]
    assert n2[3:6] == [1, 1, 0]


_INMS_04_PRECOMPUTED_CONFIG = """\
indicator:
  id: INMS-04
  contractual_id: "INMS 1.4"
  name: Disponibilidade de sistema crítico

scope:
  contract: "40/2022 - Ministério da Cultura"
  orgao: MinC

source:
  csv: inms-04.csv
  delimiter: ";"
  encoding: utf-8

quality_gates:
  checks: []

calculation:
  shape: precomputed_table
  result_column: inms_1_4_percentual
  name_column: sistema_servico_nome
  penalty_column: penalidade_pontos

target:
  operator: ">="
  value: 99.5
"""

_INMS_04_PRECOMPUTED_RAW_CSV = (
    'sistema_servico_nome;inms_1_4_percentual;penalidade_pontos\n'
    'Barramento de Integracao;99,451;1000\n'
    'Servico de Correio;99,7744;0\n'
    ';;\n'  # linha vazia/placeholder — sem medição, deve ser pulada
)

_CATEGORIAS_YAML_1_4_ONLY = """\
categorias:
  MONITORAMENTO_NOC_SOC:
    label: "Monitoramento de Ambiente (NOC/SOC)"
    inms:
      "1.4": {mode: whole_indicator}
"""

_INMS_05_PRECOMPUTED_CONFIG = """\
indicator:
  id: INMS-05
  contractual_id: "INMS 1.5"
  name: Disponibilidade de sistema não-crítico

scope:
  contract: "40/2022 - Ministério da Cultura"
  orgao: MinC

source:
  csv: inms-05.csv
  delimiter: ";"
  encoding: utf-8

quality_gates:
  checks: []

calculation:
  shape: precomputed_table
  result_column: inms_1_5_percentual
  name_column: sistema_servico_nome
  penalty_column: penalidade_pontos

target:
  operator: ">="
  value: 99.0
"""

_INMS_05_PRECOMPUTED_RAW_CSV = (
    'sistema_servico_nome;inms_1_5_percentual;penalidade_pontos\n'
    'Barramento de Integracao;99,451;1000\n'
    'Servico de Correio;99,7744;0\n'
)

_CATEGORIAS_YAML_1_5_ONLY = """\
categorias:
  MONITORAMENTO_NOC_SOC:
    label: "Monitoramento de Ambiente (NOC/SOC)"
    inms:
      "1.5": {mode: whole_indicator}
"""


def test_inms_1_4_enriched_sheet_reports_4_decimal_result_and_penalty_memory(
    tmp_path: Path,
) -> None:
    """INMS 1.4 agora usa o renderer enriquecido: identificação, resumo
    executivo, tabela com resultado a 4 casas decimais (99,451 % — não
    99,5 % que batia com a meta), e memória de penalidade por linha."""
    config_dir = tmp_path / 'configs'
    data_dir = tmp_path / 'input' / '2026' / '06'
    config_dir.mkdir(parents=True)
    data_dir.mkdir(parents=True)
    (config_dir / 'inms-04.yaml').write_text(
        _INMS_04_PRECOMPUTED_CONFIG, encoding='utf-8'
    )
    (config_dir / 'categorias.yaml').write_text(
        _CATEGORIAS_YAML_1_4_ONLY, encoding='utf-8'
    )
    (data_dir / 'inms-04.csv').write_text(
        _INMS_04_PRECOMPUTED_RAW_CSV, encoding='utf-8'
    )
    categorias_file = load_categorias(config_dir / 'categorias.yaml')
    output_path = tmp_path / 'sintetico.xlsx'

    warnings = write_sintetico_workbook(
        categorias_file, config_dir, data_dir, output_path
    )

    assert warnings == []
    wb = load_workbook(output_path)
    sheet = wb['INMS 1.4']

    # Seção 1: identificação (linha 1 = título da seção de identificação).
    assert 'Disponibilidade de sistema' in sheet['A1'].value

    # Seção 2: resumo executivo — KPIs calculados via fórmula sobre a
    # Seção 3 (ativos avaliados nas linhas 17-18: Barramento + Correio).
    kpi = [c.value for c in sheet[13]]
    assert kpi[0] == '=COUNTA(H17:H18)'
    assert kpi[1] == '=COUNTIF(H17:H18,"Sim")'
    assert kpi[2] == '=COUNTIF(H17:H18,"Não")'
    assert kpi[3] == '=SUM(G17:G18)'
    assert kpi[4] == '=IF(C13=0,"Alcançado","Não alcançado")'

    # Seção 3: cabeçalho da tabela e linhas por sistema/serviço.
    headers = [cell.value for cell in sheet[16]]
    assert headers[0] == 'Categoria'
    assert headers[1] == 'Sistema / Serviço'
    assert headers[7] == 'Meta atingida?'

    # Barramento (99,451 -> fração 0,99451; NÃO 99,5%):
    barramento = [c.value for c in sheet[17]]
    assert barramento[1] == 'Barramento de Integracao'
    # resultado a 4 casas decimais, não 0,995
    assert barramento[2] == pytest.approx(0.99451)
    assert barramento[3] == pytest.approx(0.995)
    assert barramento[5] == '=IF(E17<=0,0,ROUNDUP(E17*100/0.1,0))'
    assert barramento[6] == 1000
    assert barramento[7] == 'Não'

    correio = [c.value for c in sheet[18]]
    assert correio[1] == 'Servico de Correio'
    assert correio[7] == 'Sim'

    # Seção 4: memória de penalidade por linha.
    assert sheet['A22'].value.startswith('Barramento de Integracao')
    assert sheet['C23'].value == 'Resultado:'


def test_inms_1_5_enriched_sheet_reports_4_decimal_result_and_penalty_memory(
    tmp_path: Path,
) -> None:
    """INMS 1.5 (NOC/SOC não-crítico) tem o mesmo shape `precomputed_table`
    com `name_column` que o INMS 1.4 — usa o mesmo renderer enriquecido,
    referência INMS 1.1 (identificação, resumo executivo, resultado a 4
    casas decimais, memória de penalidade por linha)."""
    config_dir = tmp_path / 'configs'
    data_dir = tmp_path / 'input' / '2026' / '06'
    config_dir.mkdir(parents=True)
    data_dir.mkdir(parents=True)
    (config_dir / 'inms-05.yaml').write_text(
        _INMS_05_PRECOMPUTED_CONFIG, encoding='utf-8'
    )
    (config_dir / 'categorias.yaml').write_text(
        _CATEGORIAS_YAML_1_5_ONLY, encoding='utf-8'
    )
    (data_dir / 'inms-05.csv').write_text(
        _INMS_05_PRECOMPUTED_RAW_CSV, encoding='utf-8'
    )
    categorias_file = load_categorias(config_dir / 'categorias.yaml')
    output_path = tmp_path / 'sintetico.xlsx'

    warnings = write_sintetico_workbook(
        categorias_file, config_dir, data_dir, output_path
    )

    assert warnings == []
    wb = load_workbook(output_path)
    sheet = wb['INMS 1.5']

    # Seção 1: identificação (linha 1 = título da seção de identificação).
    assert 'Disponibilidade de sistema' in sheet['A1'].value

    # Seção 2: resumo executivo — KPIs calculados via fórmula sobre a
    # Seção 3 (ativos avaliados nas linhas 17-18: Barramento + Correio).
    kpi = [c.value for c in sheet[13]]
    assert kpi[0] == '=COUNTA(H17:H18)'
    assert kpi[1] == '=COUNTIF(H17:H18,"Sim")'
    assert kpi[2] == '=COUNTIF(H17:H18,"Não")'
    assert kpi[3] == '=SUM(G17:G18)'
    assert kpi[4] == '=IF(C13=0,"Alcançado","Não alcançado")'

    # Seção 3: cabeçalho da tabela e linhas por sistema/serviço.
    headers = [cell.value for cell in sheet[16]]
    assert headers[0] == 'Categoria'
    assert headers[1] == 'Sistema / Serviço'
    assert headers[7] == 'Meta atingida?'

    # Barramento (99,451 -> fração 0,99451; meta 99,0% aqui é atingida):
    barramento = [c.value for c in sheet[17]]
    assert barramento[1] == 'Barramento de Integracao'
    assert barramento[2] == pytest.approx(0.99451)
    assert barramento[3] == pytest.approx(0.99)
    assert barramento[6] == 1000
    assert barramento[7] == 'Sim'

    correio = [c.value for c in sheet[18]]
    assert correio[1] == 'Servico de Correio'
    assert correio[7] == 'Sim'

    # Seção 4: memória de penalidade por linha.
    assert sheet['A22'].value.startswith('Barramento de Integracao')
    assert sheet['C23'].value == 'Resultado:'


_INMS_09_PRECOMPUTED_CONFIG = """\
indicator:
  id: INMS-09
  contractual_id: "INMS 1.9"
  name: Tempo médio de implementação de uma mudança

scope:
  contract: "40/2022 - Ministério da Cultura"
  orgao: MinC

source:
  csv: inms-09.csv
  delimiter: ";"
  encoding: utf-8

quality_gates:
  checks: []

calculation:
  shape: precomputed_table
  result_column: inms_1_9_percentual
  name_column: ambiente_nome
  penalty_column: penalidade_pontos

target:
  operator: ">="
  value: 90.0
"""

_INMS_09_PRECOMPUTED_RAW_CSV = (
    'ambiente_nome;inms_1_9_percentual;penalidade_pontos\n'
    'Barramento de Integracao;99,5;1000\n'
    'Servico de Correio;99,8;0\n'
)

_CATEGORIAS_YAML_1_9_ONLY = """\
categorias:
  MONITORAMENTO_NOC_SOC:
    label: "Monitoramento de Ambiente (NOC/SOC)"
    inms:
      "1.9": {mode: whole_indicator}
"""

_INMS_08_POINTS_CONFIG = """\
indicator:
  id: INMS-08
  contractual_id: "INMS 1.8"
  name: Ocorrências de Desconformidade Técnica

scope:
  contract: "40/2022 - Ministério da Cultura"
  orgao: MinC

source:
  csv: inms-08.csv
  delimiter: ";"
  encoding: utf-8

quality_gates:
  checks: []

calculation:
  shape: precomputed_table
  result_column: inms_1_8_total_pdt
  result_is_percent: false
  name_column: servico_nome
  penalty_column: pontos_acima_meta

target:
  operator: "<="
  value: 0.0
"""

_INMS_08_POINTS_RAW_CSV = (
    'servico_nome;inms_1_8_total_pdt;pontos_acima_meta\n'
    'Barramento de Integracao;3;300\n'
    'Servico de Correio;0;0\n'
)

_CATEGORIAS_YAML_1_8_ONLY = """\
categorias:
  MONITORAMENTO_NOC_SOC:
    label: "Monitoramento de Ambiente (NOC/SOC)"
    inms:
      "1.8": {mode: whole_indicator}
"""


def test_inms_1_9_and_1_13_use_enriched_precomputed_audit_renderer(
    tmp_path: Path,
) -> None:
    """INMS 1.9 e 1.13 têm o mesmo shape `precomputed_table` percentual com
    `name_column` que 1.4/1.5/1.14 — usam o mesmo renderer enriquecido
    (identificação, resumo executivo, resultado a 4 casas decimais, memória
    de penalidade), não o renderer plano de `Item`/`Resultado`."""
    config_dir = tmp_path / 'configs'
    data_dir = tmp_path / 'input' / '2026' / '06'
    config_dir.mkdir(parents=True)
    data_dir.mkdir(parents=True)
    (config_dir / 'inms-09.yaml').write_text(
        _INMS_09_PRECOMPUTED_CONFIG, encoding='utf-8'
    )
    (config_dir / 'categorias.yaml').write_text(
        _CATEGORIAS_YAML_1_9_ONLY, encoding='utf-8'
    )
    (data_dir / 'inms-09.csv').write_text(
        _INMS_09_PRECOMPUTED_RAW_CSV, encoding='utf-8'
    )
    categorias_file = load_categorias(config_dir / 'categorias.yaml')
    output_path = tmp_path / 'sintetico.xlsx'

    warnings = write_sintetico_workbook(
        categorias_file, config_dir, data_dir, output_path
    )

    assert warnings == []
    wb = load_workbook(output_path)
    sheet = wb['INMS 1.9']

    assert 'Disponibilidade de sistema' in sheet['A1'].value
    headers = [cell.value for cell in sheet[16]]
    assert headers[:8] == [
        'Categoria',
        'Sistema / Serviço',
        'Resultado',
        'Meta',
        'Desvio vs Meta',
        'Faixas 0,1%',
        'Penalidade',
        'Meta atingida?',
    ]
    barramento = [c.value for c in sheet[17]]
    assert barramento[1] == 'Barramento de Integracao'
    assert barramento[2] == pytest.approx(0.995)
    assert barramento[7] == 'Sim'


def test_precomputed_table_sheet_plain_kept_for_other_precomputed_inms(
    tmp_path: Path,
) -> None:
    """O renderer precomputed plano segue vigente para INMS pontuais
    (`result_is_percent: false`, mesmo shape/formato do INMS 1.8 real) —
    o renderer enriquecido assume escala percentual (fração/PCT4) e
    quebraria a leitura de um resultado em pontos. Percentuais com
    `name_column`/`scope.contract` (1.9 incluso) agora usam o renderer
    enriquecido — ver o teste
    `test_inms_1_9_and_1_13_use_enriched_precomputed_audit_renderer`."""
    config_dir = tmp_path / 'configs'
    data_dir = tmp_path / 'input' / '2026' / '06'
    config_dir.mkdir(parents=True)
    data_dir.mkdir(parents=True)
    (config_dir / 'inms-08.yaml').write_text(
        _INMS_08_POINTS_CONFIG, encoding='utf-8'
    )
    (config_dir / 'categorias.yaml').write_text(
        _CATEGORIAS_YAML_1_8_ONLY, encoding='utf-8'
    )
    (data_dir / 'inms-08.csv').write_text(
        _INMS_08_POINTS_RAW_CSV, encoding='utf-8'
    )
    categorias_file = load_categorias(config_dir / 'categorias.yaml')
    output_path = tmp_path / 'sintetico.xlsx'

    warnings = write_sintetico_workbook(
        categorias_file, config_dir, data_dir, output_path
    )

    assert warnings == []
    wb = load_workbook(output_path)
    sheet = wb['INMS 1.8']
    assert tuple(cell.value for cell in sheet[1]) == (
        'Categoria',
        'Nível',
        'Item',
        'Resultado',
        'Meta atingida?',
        'Penalidade',
    )
    data_rows = [[c.value for c in row] for row in sheet.iter_rows(min_row=2)]
    assert data_rows == [
        [
            'Monitoramento de Ambiente (NOC/SOC)',
            'N3',
            'Barramento de Integracao',
            '3',
            '—',
            '300',
        ],
        [
            'Monitoramento de Ambiente (NOC/SOC)',
            'N3',
            'Servico de Correio',
            '0',
            '—',
            '0',
        ],
    ]


_INMS_07_RATIO_CONFIG = """\
indicator:
  id: INMS-07
  contractual_id: "INMS 1.7"
  name: Satisfação dos usuários

scope:
  contract: "40/2022 - Ministério da Cultura"
  orgao: MinC

source:
  csv: inms-07.csv
  delimiter: ";"
  encoding: utf-8

quality_gates:
  checks: []

calculation:
  shape: ratio
  aggregation: count_distinct
  numerator_filter:
    column: "Avaliação"
    in_values:
      - "Satisfeito"
      - "Muito Satisfeito"

target:
  operator: ">="
  value: 80.0

penalty:
  step_points: 250
  step_size_pct: 1.0
"""

_INMS_07_RATIO_RAW_CSV = (
    'Nº Ticket;Avaliação;Grupo_executor\n'
    '1;Satisfeito;N1\n'
    '2;Insatisfeito;N1\n'
    '3;Muito Satisfeito;N2\n'
    '4;Satisfeito;N2\n'
)

_CATEGORIAS_YAML_1_7_ONLY = """\
categorias:
  ATENDIMENTO_N1:
    label: "Atendimento Remoto aos Usuários"
    inms:
      "1.7": {mode: grupo_executor, in_values: ["N1"]}
  ATENDIMENTO_N2:
    label: "Atendimento Presencial aos Usuários"
    inms:
      "1.7": {mode: grupo_executor, in_values: ["N2"]}
"""


def test_inms_1_7_ratio_audit_sheet_reports_real_satisfaction_criteria(
    tmp_path: Path,
) -> None:
    """INMS 1.7 é `ratio`/`count_distinct` sem "No prazo"/`DataHoraFim`
    (pesquisa de satisfação) — o renderer genérico assumia essas colunas e
    só produzia traços (mesmo bug já corrigido no INMS 1.14). O renderer
    enriquecido conta o critério real (`numerator_filter` sobre
    "Avaliação") por grupo executor, com resumo executivo e memória de
    penalidade no nível do indicador."""
    config_dir = tmp_path / 'configs'
    data_dir = tmp_path / 'input' / '2026' / '06'
    config_dir.mkdir(parents=True)
    data_dir.mkdir(parents=True)
    (config_dir / 'inms-07.yaml').write_text(
        _INMS_07_RATIO_CONFIG, encoding='utf-8'
    )
    (config_dir / 'categorias.yaml').write_text(
        _CATEGORIAS_YAML_1_7_ONLY, encoding='utf-8'
    )
    (data_dir / 'inms-07.csv').write_text(
        _INMS_07_RATIO_RAW_CSV, encoding='utf-8'
    )
    categorias_file = load_categorias(config_dir / 'categorias.yaml')
    output_path = tmp_path / 'sintetico.xlsx'

    warnings = write_sintetico_workbook(
        categorias_file, config_dir, data_dir, output_path
    )

    assert warnings == []
    wb = load_workbook(output_path)
    sheet = wb['INMS 1.7']

    assert 'Satisfação dos usuários' in sheet['A1'].value

    kpi = [c.value for c in sheet[13]]
    assert kpi[0] == 4
    assert kpi[1] == 3
    assert kpi[2] == pytest.approx(0.75)
    assert kpi[3] == pytest.approx(0.8)
    assert kpi[4] == 'Não alcançado'

    headers = [c.value for c in sheet[16]]
    assert headers[:8] == [
        'Categoria',
        'Nível',
        'Grupo executor',
        'Linhas avaliadas',
        'Atenderam critério',
        'Não atenderam',
        '% resultado',
        'Meta atingida?',
    ]

    rows_by_grupo = {
        row[2].value: row for row in sheet.iter_rows(min_row=17, max_row=18)
    }
    n1 = [c.value for c in rows_by_grupo['N1']]
    assert n1[3:6] == [2, 1, 1]
    assert n1[6] == pytest.approx(0.5)
    assert n1[7] == 'Não'
    n2 = [c.value for c in rows_by_grupo['N2']]
    assert n2[3:6] == [2, 2, 0]
    assert n2[6] == pytest.approx(1.0)
    assert n2[7] == 'Sim'

    assert (
        sheet['A20'].value
        == 'SEÇÃO 4 · MEMÓRIA DA PENALIDADE (CÁLCULO INDICADOR)'
    )
    assert sheet['B21'].value == pytest.approx(0.8)
    assert sheet['B22'].value == pytest.approx(0.75)


_INMS_12_RATIO_CONFIG = """\
indicator:
  id: INMS-12
  contractual_id: "INMS 1.12"
  name: Índice de chamadas telefônicas atendidas em até 20 segundos

scope:
  contract: "40/2022 - Ministério da Cultura"
  orgao: MinC

source:
  csv: inms-12.csv
  delimiter: ";"
  encoding: utf-8

quality_gates:
  checks: []

calculation:
  shape: ratio
  aggregation: count_distinct
  numerator_filter:
    column: "ESPERA"
    max_seconds: 20

target:
  operator: ">="
  value: 95.0

penalty:
  step_points: 25
  step_size_pct: 0.1
"""

_INMS_12_RATIO_RAW_CSV = 'Chamada;ESPERA\n1;0:00:15\n2;0:00:45\n3;0:00:05\n'

_CATEGORIAS_YAML_1_12_ONLY = """\
categorias:
  ATENDIMENTO_N1:
    label: "Atendimento Remoto aos Usuários"
    inms:
      "1.12": {mode: whole_indicator}
"""


def test_inms_1_12_ratio_audit_sheet_handles_whole_indicator_duration_filter(
    tmp_path: Path,
) -> None:
    """INMS 1.11/1.12 são `whole_indicator` (sem `Grupo_executor`) com
    `numerator_filter` do tipo `DurationAtMost` (coluna `ESPERA`) — mesmo
    renderer enriquecido do INMS 1.7, com uma única linha "(indicador
    inteiro)" na Seção 3."""
    config_dir = tmp_path / 'configs'
    data_dir = tmp_path / 'input' / '2026' / '06'
    config_dir.mkdir(parents=True)
    data_dir.mkdir(parents=True)
    (config_dir / 'inms-12.yaml').write_text(
        _INMS_12_RATIO_CONFIG, encoding='utf-8'
    )
    (config_dir / 'categorias.yaml').write_text(
        _CATEGORIAS_YAML_1_12_ONLY, encoding='utf-8'
    )
    (data_dir / 'inms-12.csv').write_text(
        _INMS_12_RATIO_RAW_CSV, encoding='utf-8'
    )
    categorias_file = load_categorias(config_dir / 'categorias.yaml')
    output_path = tmp_path / 'sintetico.xlsx'

    warnings = write_sintetico_workbook(
        categorias_file, config_dir, data_dir, output_path
    )

    assert warnings == []
    wb = load_workbook(output_path)
    sheet = wb['INMS 1.12']

    kpi = [c.value for c in sheet[13]]
    assert kpi[0] == 3
    assert kpi[1] == 2
    assert kpi[2] == pytest.approx(2 / 3)
    assert kpi[4] == 'Não alcançado'

    detail = [c.value for c in sheet[17]]
    assert detail[2] == '(indicador inteiro)'
    assert detail[3:6] == [3, 2, 1]


_INMS_06_CONFIG = """\
indicator:
  id: INMS-06
  contractual_id: "INMS 1.6"
  name: Eficácia no tratamento de chamados

scope:
  contract: "40/2022 - Ministério da Cultura"
  orgao: MinC

source:
  csv: inms-06.csv
  delimiter: ","
  encoding: utf-8
  unfilterable: true

quality_gates:
  checks: []

calculation:
  shape: ratio
  aggregation: sum
  denominator_filter:
    column: "Acordo de Nível de Serviço"
    not_equals: TOTAIS
  sum_numerator_column: "Total de Chamados"
  sum_numerator_subtract_column: "Total de Chamados Reabertos"

target:
  operator: ">="
  value: 97.0

penalty:
  step_points: 200
  step_size_pct: 0.5
"""

_INMS_06_RAW_CSV = (
    'Acordo de Nível de Serviço,Total de Chamados,Total de Chamados Reabertos\n'
    'SLA A,10,1\n'
    'SLA A,10,0\n'
    'SLA B,5,0\n'
    'TOTAIS,25,1\n'
)

_CATEGORIAS_YAML_1_6_ONLY = """\
categorias:
  OPERACAO_N3:
    label: "Operação e Sustentação da Infraestrutura de TI"
    inms:
      "1.6": {mode: whole_indicator}
"""


def test_ratio_sum_subtract_sheet_aggregates_one_row_per_group_excluding_totais(
    tmp_path: Path,
) -> None:
    config_dir = tmp_path / 'configs'
    data_dir = tmp_path / 'input' / '2026' / '06'
    config_dir.mkdir(parents=True)
    data_dir.mkdir(parents=True)
    (config_dir / 'inms-06.yaml').write_text(_INMS_06_CONFIG, encoding='utf-8')
    (config_dir / 'categorias.yaml').write_text(
        _CATEGORIAS_YAML_1_6_ONLY, encoding='utf-8'
    )
    (data_dir / 'inms-06.csv').write_text(_INMS_06_RAW_CSV, encoding='utf-8')
    categorias_file = load_categorias(config_dir / 'categorias.yaml')
    output_path = tmp_path / 'sintetico.xlsx'

    warnings = write_sintetico_workbook(
        categorias_file, config_dir, data_dir, output_path
    )

    assert warnings == []
    wb = load_workbook(output_path)
    sheet = wb['INMS 1.6']

    assert 'Eficácia no tratamento de chamados' in sheet['A1'].value

    # Resumo executivo: TOTAIS excluída (denominator_filter), indicador
    # inteiro = (25-1)/25 = 96%, abaixo da meta de 97%.
    kpi = [c.value for c in sheet[13]]
    assert kpi[0] == 25
    assert kpi[1] == 24
    assert kpi[2] == pytest.approx(0.96)
    assert kpi[3] == pytest.approx(0.97)
    assert kpi[4] == 'Não alcançado'

    headers = [cell.value for cell in sheet[16]]
    assert headers[:7] == [
        'Categoria',
        'Nível',
        'Acordo de Nível de Serviço',
        'Total de Chamados',
        'Total de Chamados Reabertos',
        '% resultado',
        'Meta atingida?',
    ]
    # SLA A soma as 2 linhas (20/1); SLA B fica com sua própria linha.
    data_rows = [
        [c.value for c in row]
        for row in sheet.iter_rows(min_row=17, max_row=18)
    ]
    sla_a = data_rows[0]
    assert sla_a[2] == 'SLA A'
    assert sla_a[3:5] == [20, 1]
    assert sla_a[5] == pytest.approx(0.95)
    assert sla_a[6] == 'Não'
    sla_b = data_rows[1]
    assert sla_b[2] == 'SLA B'
    assert sla_b[3:5] == [5, 0]
    assert sla_b[5] == pytest.approx(1.0)
    assert sla_b[6] == 'Sim'

    # Memória de penalidade: diff = 97-96 = 1 p.p.; 1/0.5 * 200 = 400.
    assert (
        sheet['A20'].value
        == 'SEÇÃO 4 · MEMÓRIA DA PENALIDADE (CÁLCULO INDICADOR)'
    )
    assert sheet['B25'].value == pytest.approx(400.0)


_PRAZOS_RAW_CSV = (
    'Demanda,Criticidade,Prazo máximo para atendimento\n'
    'Incidentes,Alta,2h (horas corridas)\n'
    'Requisições,Alta,4h (horas corridas)\n'
    'Requisições,Média,8h (horas corridas)\n'
    'Requisições,Baixa,16h (horas corridas)\n'
    'Projetos,-,Prazo acordado entre Contratante e Contratada\n'
)


def test_prazos_sheet_is_first_and_formats_the_reference_table(
    tmp_path: Path,
) -> None:
    config_dir, data_dir = _write_fixture(tmp_path, include_inms_04_csv=True)
    categorias_file = load_categorias(config_dir / 'categorias.yaml')
    output_path = tmp_path / 'sintetico.xlsx'
    prazos_path = tmp_path / 'prazos.csv'
    prazos_path.write_text(_PRAZOS_RAW_CSV, encoding='utf-8')

    warnings = write_sintetico_workbook(
        categorias_file,
        config_dir,
        data_dir,
        output_path,
        prazos_path=prazos_path,
    )

    assert warnings == []
    wb = load_workbook(output_path)
    assert wb.sheetnames[0] == 'Prazos'
    sheet = wb['Prazos']
    assert sheet['B1'].value == (
        'DEMONSTRATIVO DE EXECUÇÃO DOS SERVIÇOS DE INFRAESTRUTURA DE TI'
    )
    assert sheet['B2'].value == '=Capa!B2'
    assert sheet['B4'].value == 'PRAZOS MÁXIMOS PARA ATENDIMENTO'
    assert sheet['B8'].value == 'Demanda'
    assert sheet['C8'].value == 'Criticidade'
    # "2h (horas corridas)" ganha a forma padronizada (spec §5.5).
    assert sheet['B9'].value == 'Incidentes'
    assert sheet['D9'].value == '2 horas corridas'
    # "-" é ambíguo — vira "Não aplicável" para a linha de Projetos.
    assert sheet['C13'].value == 'Não aplicável'


def test_prazos_sheet_missing_file_warns_and_skips(tmp_path: Path) -> None:
    config_dir, data_dir = _write_fixture(tmp_path, include_inms_04_csv=True)
    categorias_file = load_categorias(config_dir / 'categorias.yaml')
    output_path = tmp_path / 'sintetico.xlsx'
    prazos_path = tmp_path / 'prazos.csv'  # não existe

    warnings = write_sintetico_workbook(
        categorias_file,
        config_dir,
        data_dir,
        output_path,
        prazos_path=prazos_path,
    )

    assert len(warnings) == 1
    assert 'Prazos' in warnings[0]
    wb = load_workbook(output_path)
    assert 'Prazos' not in wb.sheetnames


def test_prazos_sheet_omitted_when_prazos_path_not_given(
    tmp_path: Path,
) -> None:
    config_dir, data_dir = _write_fixture(tmp_path, include_inms_04_csv=True)
    categorias_file = load_categorias(config_dir / 'categorias.yaml')
    output_path = tmp_path / 'sintetico.xlsx'

    warnings = write_sintetico_workbook(
        categorias_file, config_dir, data_dir, output_path
    )

    assert warnings == []
    wb = load_workbook(output_path)
    assert 'Prazos' not in wb.sheetnames


_CAPA_RAW_CSV = (
    'Campo;Valor\nNúmero do contrato;40/2022\n'
    'Processo SEI;72031.010172/2020-97\n'
    'Portaria Equipe;SGI/MINC 193/2026\n'
)
_EQUIPE_RAW_CSV = (
    'FUNÇÃO,NOME,SIAPE\n'
    'Gestor do Contrato,Thiago Augusto Arcanjo Lima,1500967\n'
    'Fiscal Técnico,João Antônio Carvalho Monteiro de Oliveira,1499628\n'
)
_OBJETOS_RAW_CSV = (
    'Item,Categoria,Valor\n'
    '1,Central de Serviços," R$  148.205,54 "\n'
    '2,GT dos Projetos e Operações," R$  77.654,90 "\n'
)


def test_capa_equipe_prazos_sheets_come_first_in_order(tmp_path: Path) -> None:
    config_dir, data_dir = _write_fixture(tmp_path, include_inms_04_csv=True)
    categorias_file = load_categorias(config_dir / 'categorias.yaml')
    output_path = tmp_path / 'sintetico.xlsx'
    capa_path = tmp_path / 'capa.csv'
    capa_path.write_text(_CAPA_RAW_CSV, encoding='utf-8-sig')
    equipe_path = tmp_path / 'equipe.csv'
    equipe_path.write_text(_EQUIPE_RAW_CSV, encoding='utf-8-sig')
    prazos_path = tmp_path / 'prazos.csv'
    prazos_path.write_text(_PRAZOS_RAW_CSV, encoding='utf-8')

    warnings = write_sintetico_workbook(
        categorias_file,
        config_dir,
        data_dir,
        output_path,
        capa_path=capa_path,
        equipe_path=equipe_path,
        prazos_path=prazos_path,
    )

    assert warnings == []
    wb = load_workbook(output_path)
    assert wb.sheetnames[:3] == ['Capa', 'Equipe', 'Prazos']
    assert 'Objetos' not in wb.sheetnames

    capa_sheet = wb['Capa']
    assert capa_sheet['B1'].value == (
        'DEMONSTRATIVO DE EXECUÇÃO DOS SERVIÇOS DE INFRAESTRUTURA DE TI'
    )
    # Sem campo "Contrato" no CSV (fixture não tem), o subtítulo cai para
    # texto simples em vez da fórmula que referenciaria essa linha.
    assert capa_sheet['B2'].value == 'Contrato nº 40/2022'
    assert capa_sheet['B4'].value == 'INFORMAÇÕES INICIAIS'
    assert capa_sheet['B6'].value == 'Campo'
    assert capa_sheet['D6'].value == 'Valor'
    assert capa_sheet['B7'].value == 'Número do contrato'
    assert capa_sheet['D7'].value == '40/2022'
    assert capa_sheet['D7'].number_format == '@'
    assert capa_sheet['B8'].value == 'Processo SEI'
    assert capa_sheet['D8'].value == '72031.010172/2020-97'

    equipe_sheet = wb['Equipe']
    assert equipe_sheet['B1'].value == (
        'DEMONSTRATIVO DE EXECUÇÃO DOS SERVIÇOS DE INFRAESTRUTURA DE TI'
    )
    assert equipe_sheet['B2'].value == '=Capa!B2'
    assert equipe_sheet['B4'].value == (
        'EQUIPE DE GESTÃO E FISCALIZAÇÃO DO CONTRATO'
    )
    assert equipe_sheet['B6'].value == 'FUNÇÃO'
    assert equipe_sheet['B7'].value == 'Gestor do Contrato'
    assert equipe_sheet['D7'].value == 'Thiago Augusto Arcanjo Lima'
    assert equipe_sheet['G7'].value == '1500967'


def test_objetos_is_appended_below_capa_not_a_separate_sheet(
    tmp_path: Path,
) -> None:
    config_dir, data_dir = _write_fixture(tmp_path, include_inms_04_csv=True)
    categorias_file = load_categorias(config_dir / 'categorias.yaml')
    output_path = tmp_path / 'sintetico.xlsx'
    capa_path = tmp_path / 'capa.csv'
    capa_path.write_text(_CAPA_RAW_CSV, encoding='utf-8-sig')
    objetos_path = tmp_path / 'objetos.csv'
    objetos_path.write_text(_OBJETOS_RAW_CSV, encoding='utf-8-sig')

    warnings = write_sintetico_workbook(
        categorias_file,
        config_dir,
        data_dir,
        output_path,
        capa_path=capa_path,
        objetos_path=objetos_path,
    )

    assert warnings == []
    wb = load_workbook(output_path)
    assert 'Objetos' not in wb.sheetnames
    sheet = wb['Capa']
    # Identificação (3 campos no fixture: Número do contrato, Processo SEI,
    # Portaria Equipe) começa na linha 7 e termina na 9; a Seção 3 (Item/
    # Categoria/Valor) começa depois de uma linha em branco.
    assert sheet['B11'].value == 'Item'
    assert sheet['C11'].value == 'Categoria'
    assert sheet['D11'].value == 'Valor'
    assert sheet['B12'].value == '1'
    assert sheet['C12'].value == 'Central de Serviços'
    assert sheet['D12'].value == 148205.54
    assert sheet['B13'].value == '2'
    assert sheet['C13'].value == 'GT dos Projetos e Operações'
    assert sheet['D13'].value == 77654.90
    assert sheet['C14'].value == 'Total mensal'
    assert sheet['D14'].value == '=SUM(D12:D13)'


def test_objetos_not_appended_when_capa_path_missing(tmp_path: Path) -> None:
    config_dir, data_dir = _write_fixture(tmp_path, include_inms_04_csv=True)
    categorias_file = load_categorias(config_dir / 'categorias.yaml')
    output_path = tmp_path / 'sintetico.xlsx'
    objetos_path = tmp_path / 'objetos.csv'
    objetos_path.write_text(_OBJETOS_RAW_CSV, encoding='utf-8-sig')

    warnings = write_sintetico_workbook(
        categorias_file,
        config_dir,
        data_dir,
        output_path,
        objetos_path=objetos_path,
    )

    assert len(warnings) == 1
    assert 'objetos' in warnings[0].lower()
    wb = load_workbook(output_path)
    assert 'Capa' not in wb.sheetnames
    assert 'Objetos' not in wb.sheetnames


def test_capa_sheet_missing_file_warns_and_skips(tmp_path: Path) -> None:
    config_dir, data_dir = _write_fixture(tmp_path, include_inms_04_csv=True)
    categorias_file = load_categorias(config_dir / 'categorias.yaml')
    output_path = tmp_path / 'sintetico.xlsx'
    capa_path = tmp_path / 'capa.csv'  # não existe

    warnings = write_sintetico_workbook(
        categorias_file, config_dir, data_dir, output_path, capa_path=capa_path
    )

    assert len(warnings) == 1
    assert 'Capa' in warnings[0]
    wb = load_workbook(output_path)
    assert 'Capa' not in wb.sheetnames


def test_equipe_sheet_omitted_when_equipe_path_not_given(
    tmp_path: Path,
) -> None:
    config_dir, data_dir = _write_fixture(tmp_path, include_inms_04_csv=True)
    categorias_file = load_categorias(config_dir / 'categorias.yaml')
    output_path = tmp_path / 'sintetico.xlsx'

    warnings = write_sintetico_workbook(
        categorias_file, config_dir, data_dir, output_path
    )

    assert warnings == []
    wb = load_workbook(output_path)
    assert 'Equipe' not in wb.sheetnames
