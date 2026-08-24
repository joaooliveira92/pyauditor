"""Caracterização da aba enriquecida do INMS 1.2
(`pyauditor.excel.inms_1_2.write.write_sheet`), acionada por `sintetico.py`
quando o CSV bruto tem as colunas de detalhe exigidas (as mesmas do INMS 1.1
mais `SLA`, usada para segmentar por prioridade). Espelha
`test_inms_1_1_audit.py` — shape `segmented_ratio` (3 sub-ratios por
prioridade Alta/Média/Baixa, cada um com seu próprio `step_points`, sem
`base_points`), em vez do `ratio` único do INMS 1.1.
"""

from datetime import date
from pathlib import Path

from openpyxl import load_workbook

from pyauditor.config.categorias import load_categorias
from pyauditor.excel.sintetico import write_sintetico_workbook
from pyauditor.periodo import PeriodoAfericao

_INMS_02_CONFIG = """\
indicator:
  id: INMS-02
  contractual_id: "INMS 1.2"
  name: Requisições atendidas dentro do prazo

scope:
  contract: "40/2022 - Ministério da Cultura"
  orgao: MinC

source:
  csv: inms-02.csv
  delimiter: ";"
  encoding: utf-8
  period_column: "DataHoraSolicitacao"

quality_gates:
  checks:
    - type: in_set
      column: "No prazo"
      values: ["S", "N"]

calculation:
  shape: segmented_ratio
  step_size_pct: 0.1
  categories:
    - name: Alta
      denominator_filter: {column: SLA, contains: Alta}
      numerator_filter: {column: "No prazo", equals: S}
      step_points: 20
    - name: Média
      denominator_filter: {column: SLA, contains: Média}
      numerator_filter: {column: "No prazo", equals: S}
      step_points: 15
    - name: Baixa
      denominator_filter: {column: SLA, contains: Baixa}
      numerator_filter: {column: "No prazo", equals: S}
      step_points: 10

target:
  operator: ">="
  value: 95.0
"""

_CATEGORIAS_YAML = """\
categorias:
  ATENDIMENTO_N1:
    label: "Atendimento Remoto aos Usuários"
    inms:
      "1.2": {mode: grupo_executor, in_values: ["N1"]}
  ATENDIMENTO_N2:
    label: "Atendimento Presencial aos Usuários"
    inms:
      "1.2": {mode: grupo_executor, in_values: ["N2"]}
"""

# Todas as colunas exigidas por `inms_1_2.write.has_required_columns`
# (base do INMS 1.1 + `SLA`) — 1 requisição por prioridade, todas dentro do
# grupo N1, exceto a 3ª (N2).
_INMS_02_RAW_CSV_ENRIQUECIDO = (
    'Nº Solicitacao;Atividades;SLA;DataHoraSolicitacao;DataHoraLimite;'
    'DataHoraFim;No prazo;Grupo_executor;TecnicoExecutor\n'
    '1;Dúvida;(CIT) Requisição - Alta 2 horas;01/06/2026 08:00;'
    '01/06/2026 10:00;01/06/2026 09:30;S;N1;Fulano\n'
    '2;Manutenção;(CIT) Requisição - Média 8 horas;01/06/2026 09:00;'
    '01/06/2026 17:00;02/06/2026 09:00;N;N1;Fulano\n'
    '3;Acesso;(CIT) Requisição - Baixa 16 horas;01/06/2026 08:00;'
    '02/06/2026 00:00;01/06/2026 09:00;S;N2;Beltrano\n'
)

_MINIMAL_CSV_SEM_DETALHE = (
    # Tem as colunas mínimas que `measurement_source` exige (period_column,
    # quality gate, e a coluna `SLA` referenciada pelo `calculation` do
    # config) — mas falta o restante das colunas de detalhe (`Atividades`,
    # `Nº Solicitacao`, `DataHoraLimite`, `DataHoraFim`,
    # `TecnicoExecutor`), então `has_required_columns` continua `False`.
    'DataHoraSolicitacao;No prazo;Grupo_executor;SLA\n'
    '01/06/2026 08:00;S;N1;(CIT) Requisição - Alta 2 horas\n'
)


def _write_fixture(tmp_path: Path) -> tuple[Path, Path]:
    config_dir = tmp_path / 'configs'
    data_dir = tmp_path / 'input' / '2026' / '06'
    config_dir.mkdir(parents=True)
    data_dir.mkdir(parents=True)

    (config_dir / 'inms-02.yaml').write_text(_INMS_02_CONFIG, encoding='utf-8')
    (config_dir / 'categorias.yaml').write_text(
        _CATEGORIAS_YAML, encoding='utf-8'
    )
    (data_dir / 'inms-02.csv').write_text(
        _INMS_02_RAW_CSV_ENRIQUECIDO, encoding='utf-8'
    )

    return config_dir, data_dir


def test_enriched_sheet_is_used_when_raw_csv_has_detail_columns(
    tmp_path: Path,
) -> None:
    config_dir, data_dir = _write_fixture(tmp_path)
    categorias_file = load_categorias(config_dir / 'categorias.yaml')
    output_path = tmp_path / 'sintetico.xlsx'
    periodo = PeriodoAfericao(date(2026, 6, 1), date(2026, 6, 30))

    warnings = write_sintetico_workbook(
        categorias_file, config_dir, data_dir, output_path, periodo=periodo
    )

    assert warnings == []
    wb = load_workbook(output_path)
    sheet = wb['INMS 1.2']

    assert (
        sheet['A1'].value == 'INMS 1.2 – Requisições atendidas dentro do prazo'
    )

    section_bars = {
        cell.value
        for row in sheet.iter_rows(min_col=1, max_col=1)
        for cell in row
        if isinstance(cell.value, str) and cell.value.startswith('SEÇÃO')
    }
    assert section_bars == {
        'SEÇÃO 1 · IDENTIFICAÇÃO',
        'SEÇÃO 2 · RESUMO EXECUTIVO',
        'SEÇÃO 3 · MEMÓRIA DO CÁLCULO CONSOLIDADO',
        'SEÇÃO 4 · DETALHAMENTO POR GRUPO EXECUTOR',
        'SEÇÃO 5 · SUBTOTAIS POR NÍVEL (informação gerencial)',
        'SEÇÃO 6 · REQUISIÇÕES FORA DO PRAZO',
        'SEÇÃO 7 · AUDITORIA DO PRAZO CONTRATUAL',
        'SEÇÃO 8 · TEMPO CORRIDO MÉDIO ATÉ A RESOLUÇÃO',
        'SEÇÃO 9 · PENALIDADE (CÁLCULO PRELIMINAR)',
    }


def test_section_2_has_one_kpi_row_per_category_plus_pooled_total(
    tmp_path: Path,
) -> None:
    config_dir, data_dir = _write_fixture(tmp_path)
    categorias_file = load_categorias(config_dir / 'categorias.yaml')
    output_path = tmp_path / 'sintetico.xlsx'
    periodo = PeriodoAfericao(date(2026, 6, 1), date(2026, 6, 30))

    write_sintetico_workbook(
        categorias_file, config_dir, data_dir, output_path, periodo=periodo
    )

    wb = load_workbook(output_path)
    sheet = wb['INMS 1.2']

    labels = [
        cell.value
        for row in sheet.iter_rows(min_col=1, max_col=1, max_row=25)
        for cell in row
        if isinstance(cell.value, str)
        and ('Prioridade' in cell.value or 'Consolidado' in cell.value)
    ]
    assert labels == [
        'Prioridade Alta (SLA)',
        'Prioridade Média (SLA)',
        'Prioridade Baixa (SLA)',
        'Consolidado (3 categorias — pooled)',
    ]

    # KPI de "Alta" (1 requisição, dentro do prazo).
    assert sheet['B14'].value == (
        '=COUNTIFS($AP$2:$AP$4,"Sim",$AB$2:$AB$4,"*Alta*")'
    )
    assert sheet['C14'].value == (
        '=COUNTIFS($AP$2:$AP$4,"Sim",$AB$2:$AB$4,"*Alta*",$X$2:$X$4,"S")'
    )
    assert sheet['E14'].value == '=IF(B14=0,"Sem ocorrências",C14/B14)'

    # Linha consolidada (pooled) soma os numeradores/denominadores das 3
    # categorias — não recalcula a partir do bloco de apoio bruto.
    assert sheet['B20'].value == '=B14+B16+B18'
    assert sheet['C20'].value == '=C14+C16+C18'
    assert sheet['D20'].value == '=D14+D16+D18'
    # Situação consolidada só é "Meta atingida" quando as 3 categorias
    # individualmente atingem a meta (replica
    # `SegmentedRatioStrategy.calculate`'s `conforms`).
    assert sheet['G20'].value == (
        '=IF(B20=0,"Sem ocorrências",IF(AND(G14="Meta atingida",'
        'G16="Meta atingida",G18="Meta atingida"),"Meta atingida",'
        '"Meta não atingida"))'
    )


def test_section_5_cross_check_uses_pooled_row_not_fixed_row_13(
    tmp_path: Path,
) -> None:
    """O INMS 1.2 tem 3 blocos de KPI (Seção 2) antes da linha consolidada —
    a verificação cruzada da Seção 5 precisa comparar contra a linha pooled
    de fato (20 nesta fixture), não a linha 13 fixa que o INMS 1.1 usa."""
    config_dir, data_dir = _write_fixture(tmp_path)
    categorias_file = load_categorias(config_dir / 'categorias.yaml')
    output_path = tmp_path / 'sintetico.xlsx'
    periodo = PeriodoAfericao(date(2026, 6, 1), date(2026, 6, 30))

    write_sintetico_workbook(
        categorias_file, config_dir, data_dir, output_path, periodo=periodo
    )

    wb = load_workbook(output_path)
    sheet = wb['INMS 1.2']
    check_label_row = next(
        cell.row
        for row in sheet.iter_rows(min_col=1, max_col=1)
        for cell in row
        if cell.value == 'Verificação cruzada (Seção 5 = Seção 2/3):'
    )
    assert isinstance(check_label_row, int)
    formula = sheet.cell(row=check_label_row, column=2).value
    assert isinstance(formula, str)
    assert 'E20' in formula
    assert 'E13' not in formula


def test_section_6_lists_out_of_deadline_requests_with_priority_column(
    tmp_path: Path,
) -> None:
    config_dir, data_dir = _write_fixture(tmp_path)
    categorias_file = load_categorias(config_dir / 'categorias.yaml')
    output_path = tmp_path / 'sintetico.xlsx'
    periodo = PeriodoAfericao(date(2026, 6, 1), date(2026, 6, 30))

    write_sintetico_workbook(
        categorias_file, config_dir, data_dir, output_path, periodo=periodo
    )

    wb = load_workbook(output_path)
    sheet = wb['INMS 1.2']

    s6_bar_row = next(
        cell.row
        for row in sheet.iter_rows(min_col=1, max_col=1)
        for cell in row
        if cell.value == 'SEÇÃO 6 · REQUISIÇÕES FORA DO PRAZO'
    )
    assert isinstance(s6_bar_row, int)
    header_row = s6_bar_row + 1
    assert sheet.cell(row=header_row, column=4).value == 'Prioridade (SLA)'
    first_data_row = header_row + 1
    assert sheet.cell(row=first_data_row, column=4).value == (
        '=IFERROR(INDEX($AB$2:$AB$4,MATCH(1,$AH$2:$AH$4,0)),"")'
    )


def test_section_9_penalty_has_no_base_points_and_sums_three_categories(
    tmp_path: Path,
) -> None:
    config_dir, data_dir = _write_fixture(tmp_path)
    categorias_file = load_categorias(config_dir / 'categorias.yaml')
    output_path = tmp_path / 'sintetico.xlsx'
    periodo = PeriodoAfericao(date(2026, 6, 1), date(2026, 6, 30))

    write_sintetico_workbook(
        categorias_file, config_dir, data_dir, output_path, periodo=periodo
    )

    wb = load_workbook(output_path)
    sheet = wb['INMS 1.2']

    penalty_rows = {
        cell.value: cell.row
        for row in sheet.iter_rows(min_col=1, max_col=1)
        for cell in row
        if isinstance(cell.value, str) and cell.value.startswith('Penalidade —')
    }
    assert len(penalty_rows) == 3
    alta_label = next(k for k in penalty_rows if 'Alta' in k)
    alta_row = penalty_rows[alta_label]
    assert isinstance(alta_row, int)
    formula = sheet.cell(row=alta_row, column=2).value
    assert isinstance(formula, str)
    # Sem `base_points` — a fórmula não soma nenhum valor fixo além do
    # adicional proporcional (diferente da Seção 9 do INMS 1.1).
    assert '165' not in formula
    assert '20' in formula  # step_points de Alta

    total_row = next(
        cell.row
        for row in sheet.iter_rows(min_col=1, max_col=1)
        for cell in row
        if cell.value == 'Penalidade total (soma das 3 categorias):'
    )
    assert isinstance(total_row, int)
    total_formula = sheet.cell(row=total_row, column=2).value
    assert isinstance(total_formula, str)
    assert total_formula.count('+') == 2
    for row_num in penalty_rows.values():
        assert f'B{row_num}' in total_formula


def test_degrades_to_generic_renderer_when_sla_column_missing(
    tmp_path: Path,
) -> None:
    """CSV sem a coluna `SLA` (ou demais colunas de detalhe) não pode
    quebrar o workbook — cai no renderer genérico, como o INMS 1.1 faz para
    fixtures minimalistas."""
    config_dir, data_dir = _write_fixture(tmp_path)
    (data_dir / 'inms-02.csv').write_text(
        _MINIMAL_CSV_SEM_DETALHE, encoding='utf-8'
    )
    categorias_file = load_categorias(config_dir / 'categorias.yaml')
    output_path = tmp_path / 'sintetico.xlsx'
    periodo = PeriodoAfericao(date(2026, 6, 1), date(2026, 6, 30))

    warnings = write_sintetico_workbook(
        categorias_file, config_dir, data_dir, output_path, periodo=periodo
    )

    assert warnings == []
    wb = load_workbook(output_path)
    sheet = wb['INMS 1.2']
    # Renderer genérico: sem seções, cabeçalho fixo de
    # `_write_grupo_executor_sheet`.
    assert sheet['A1'].value == 'Categoria'
    section_bars = [
        cell.value
        for row in sheet.iter_rows(min_col=1, max_col=1)
        for cell in row
        if isinstance(cell.value, str) and cell.value.startswith('SEÇÃO')
    ]
    assert section_bars == []


def test_force_recalc_flags_are_set(tmp_path: Path) -> None:
    config_dir, data_dir = _write_fixture(tmp_path)
    categorias_file = load_categorias(config_dir / 'categorias.yaml')
    output_path = tmp_path / 'sintetico.xlsx'
    periodo = PeriodoAfericao(date(2026, 6, 1), date(2026, 6, 30))

    write_sintetico_workbook(
        categorias_file, config_dir, data_dir, output_path, periodo=periodo
    )

    wb = load_workbook(output_path)
    assert wb.calculation.fullCalcOnLoad is True
    assert wb.calculation.forceFullCalc is True
