from pathlib import Path

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
    "Nº Solicitacao;DataHoraSolicitacao;DataHoraFim;No prazo;Grupo_executor\n"
    "1;01/06/2026 08:00;01/06/2026 10:00;S;N1\n"
    "2;01/06/2026 09:00;02/06/2026 09:00;N;N1\n"
    "3;01/06/2026 08:00;01/06/2026 09:00;S;N2\n"
    "4;01/06/2026 08:00;01/06/2026 20:00;S;(CIT) - Infra\n"
    "5;01/06/2026 08:00;;N;Grupo Desconhecido\n"
)

_INMS_09_RAW_CSV = (
    "Chamado;Situação\n"
    "1;No prazo\n"
    "2;No prazo\n"
    "3;Fora do prazo\n"
)

# Anexo D, Tabela 28: 6 ativos nomeados, um por linha — mesmo formato do
# /input real (`disponibilidade_infra`), sem colunas de fila de atendimento
# (`No prazo`/`DataHoraSolicitacao`/`DataHoraFim`), que degradam pra "—".
_INMS_14_RAW_CSV = (
    "servico_infraestrutura;numerador_inms_horas;base_apuracao_horas;"
    "inms_1_14_percentual;penalidade_pontos\n"
    "File Server;715;720;99,3;250\n"
    "Telefonia;720;720;100,0;0\n"
    "Mensageria;720;720;100,0;0\n"
    "Servidores de impressão;720;720;100,0;0\n"
    "WI-FI;718;720;99,7;0\n"
    "Rede;720;720;100,0;0\n"
)


def _write_fixture(
    tmp_path: Path, *, include_inms_04_csv: bool, include_inms_14: bool = False
) -> tuple[Path, Path]:
    config_dir = tmp_path / "configs"
    data_dir = tmp_path / "input" / "2026" / "06"
    config_dir.mkdir(parents=True)
    data_dir.mkdir(parents=True)

    (config_dir / "inms-01.yaml").write_text(_INMS_01_CONFIG, encoding="utf-8")
    (config_dir / "inms-09.yaml").write_text(_INMS_09_CONFIG, encoding="utf-8")
    (config_dir / "inms-04.yaml").write_text(_INMS_04_CONFIG, encoding="utf-8")
    categorias_yaml = _CATEGORIAS_YAML_COM_1_14 if include_inms_14 else _CATEGORIAS_YAML
    (config_dir / "categorias.yaml").write_text(categorias_yaml, encoding="utf-8")

    (data_dir / "inms-01.csv").write_text(_INMS_01_RAW_CSV, encoding="utf-8")
    (data_dir / "inms-09.csv").write_text(_INMS_09_RAW_CSV, encoding="utf-8")
    if include_inms_04_csv:
        (data_dir / "inms-04.csv").write_text("Situação\nDisponível\n", encoding="utf-8")
    if include_inms_14:
        (config_dir / "inms-14.yaml").write_text(_INMS_14_CONFIG, encoding="utf-8")
        (data_dir / "inms-14.csv").write_text(_INMS_14_RAW_CSV, encoding="utf-8")

    return config_dir, data_dir


def test_sheet_names_cover_every_inms_with_categoria_entry(tmp_path: Path) -> None:
    config_dir, data_dir = _write_fixture(tmp_path, include_inms_04_csv=True)
    categorias_file = load_categorias(config_dir / "categorias.yaml")
    output_path = tmp_path / "sintetico.xlsx"

    warnings = write_sintetico_workbook(categorias_file, config_dir, data_dir, output_path)

    assert warnings == []
    wb = load_workbook(output_path)
    assert set(wb.sheetnames) == {"INMS 1.1", "INMS 1.9", "INMS 1.4"}


def test_grupo_executor_sheet_has_one_row_per_categoria_x_grupo_executor(
    tmp_path: Path,
) -> None:
    config_dir, data_dir = _write_fixture(tmp_path, include_inms_04_csv=True)
    categorias_file = load_categorias(config_dir / "categorias.yaml")
    output_path = tmp_path / "sintetico.xlsx"

    write_sintetico_workbook(categorias_file, config_dir, data_dir, output_path)

    wb = load_workbook(output_path)
    sheet = wb["INMS 1.1"]
    assert tuple(cell.value for cell in sheet[1]) == (
        "Categoria", "Nível", "Grupo executor", "Linhas", "Dentro do prazo",
        "Fora do prazo", "% bruto", "Tempo médio criação→resolução",
    )

    rows_by_grupo = {row[2].value: row for row in sheet.iter_rows(min_row=2, max_row=5)}

    n1_row = rows_by_grupo["N1"]
    assert [c.value for c in n1_row] == [
        "Atendimento Remoto aos Usuários", "N1", "N1", 2, 1, 1, "50,0%", "0d 13h",
    ]

    n2_row = rows_by_grupo["N2"]
    assert [c.value for c in n2_row] == [
        "Atendimento Presencial aos Usuários", "N2", "N2", 1, 1, 0, "100,0%", "0d 01h",
    ]

    n3_row = rows_by_grupo["(CIT) - Infra"]
    assert [c.value for c in n3_row] == [
        "Operação e Sustentação da Infraestrutura de TI", "N3", "(CIT) - Infra",
        1, 1, 0, "100,0%", "0d 12h",
    ]

    outros_row = rows_by_grupo["Grupo Desconhecido"]
    assert [c.value for c in outros_row] == [
        "outros (não contabilizado na meta)", None, "Grupo Desconhecido", 1, 0, 1, "0,0%", "—",
    ]


def test_grupo_executor_sheet_has_subtotals_by_nivel(tmp_path: Path) -> None:
    config_dir, data_dir = _write_fixture(tmp_path, include_inms_04_csv=True)
    categorias_file = load_categorias(config_dir / "categorias.yaml")
    output_path = tmp_path / "sintetico.xlsx"

    write_sintetico_workbook(categorias_file, config_dir, data_dir, output_path)

    wb = load_workbook(output_path)
    sheet = wb["INMS 1.1"]
    header_row = next(
        row[0].row for row in sheet.iter_rows(min_row=1) if row[0].value == "Subtotais por Nível"
    )
    subtotal_rows = {
        row[0].value: row[:6]
        for row in sheet.iter_rows(min_row=header_row + 2, max_row=header_row + 4)
    }

    assert [c.value for c in subtotal_rows["N1"]] == ["N1", 2, 1, 1, "50,0%", "0d 13h"]
    assert [c.value for c in subtotal_rows["N2"]] == ["N2", 1, 1, 0, "100,0%", "0d 01h"]
    assert [c.value for c in subtotal_rows["N3"]] == ["N3", 1, 1, 0, "100,0%", "0d 12h"]


def test_whole_indicator_sheet_is_single_row_no_subtotals(tmp_path: Path) -> None:
    config_dir, data_dir = _write_fixture(tmp_path, include_inms_04_csv=True)
    categorias_file = load_categorias(config_dir / "categorias.yaml")
    output_path = tmp_path / "sintetico.xlsx"

    write_sintetico_workbook(categorias_file, config_dir, data_dir, output_path)

    wb = load_workbook(output_path)
    sheet = wb["INMS 1.9"]
    data_rows = list(sheet.iter_rows(min_row=2))
    assert len(data_rows) == 1
    assert [c.value for c in data_rows[0]] == [
        "Operação e Sustentação da Infraestrutura de TI", "N3", "(indicador inteiro)",
        3, "—", "—", "—", "—",
    ]
    assert not any(
        cell.value == "Subtotais por Nível" for row in sheet.iter_rows() for cell in row
    )


def test_inms_1_14_sheet_uses_ativo_column_with_12_rows_in_categoria_blocks(
    tmp_path: Path,
) -> None:
    config_dir, data_dir = _write_fixture(
        tmp_path, include_inms_04_csv=True, include_inms_14=True
    )
    categorias_file = load_categorias(config_dir / "categorias.yaml")
    output_path = tmp_path / "sintetico.xlsx"

    warnings = write_sintetico_workbook(categorias_file, config_dir, data_dir, output_path)

    assert warnings == []
    wb = load_workbook(output_path)
    assert "INMS 1.14" in wb.sheetnames
    sheet = wb["INMS 1.14"]

    assert tuple(cell.value for cell in sheet[1]) == (
        "Categoria", "Nível", "Ativo", "Linhas",
        "Dentro do prazo", "Fora do prazo", "% bruto", "Tempo médio criação→resolução",
    )

    data_rows = list(sheet.iter_rows(min_row=2, max_row=13))
    assert len(data_rows) == 12

    # Bloco NOC/SOC (linhas 2-7) antes do bloco Operação N3 (linhas 8-13).
    noc_soc_rows = [row[2].value for row in data_rows[:6]]
    operacao_n3_rows = [row[2].value for row in data_rows[6:]]
    assert noc_soc_rows == operacao_n3_rows == [
        "File Server", "Telefonia", "Mensageria", "Servidores de impressão",
        "WI-FI", "Rede",
    ]

    first_row = data_rows[0]
    assert [cell.value for cell in first_row] == [
        "Monitoramento de Ambiente (NOC/SOC)", "N3", "File Server", 1, "—", "—", "—", "—",
    ]
    eighth_row = data_rows[6]
    assert [cell.value for cell in eighth_row] == [
        "Operação e Sustentação da Infraestrutura de TI", "N3", "File Server",
        1, "—", "—", "—", "—",
    ]


def test_inms_1_14_sheet_has_subtotals_by_categoria_not_nivel(tmp_path: Path) -> None:
    config_dir, data_dir = _write_fixture(
        tmp_path, include_inms_04_csv=True, include_inms_14=True
    )
    categorias_file = load_categorias(config_dir / "categorias.yaml")
    output_path = tmp_path / "sintetico.xlsx"

    write_sintetico_workbook(categorias_file, config_dir, data_dir, output_path)

    wb = load_workbook(output_path)
    sheet = wb["INMS 1.14"]
    header_row = next(
        row[0].row
        for row in sheet.iter_rows(min_row=1)
        if row[0].value == "Subtotais por Categoria"
    )
    assert tuple(cell.value for cell in sheet[header_row + 1][:6]) == (
        "Categoria", "Linhas", "Dentro do prazo", "Fora do prazo", "% bruto",
        "Tempo médio criação→resolução",
    )
    subtotal_rows = [
        [c.value for c in row[:6]]
        for row in sheet.iter_rows(min_row=header_row + 2, max_row=header_row + 3)
    ]
    assert subtotal_rows == [
        ["Monitoramento de Ambiente (NOC/SOC)", 6, "—", "—", "—", "—"],
        ["Operação e Sustentação da Infraestrutura de TI", 6, "—", "—", "—", "—"],
    ]


def test_nao_ativado_when_raw_csv_missing(tmp_path: Path) -> None:
    config_dir, data_dir = _write_fixture(tmp_path, include_inms_04_csv=False)
    categorias_file = load_categorias(config_dir / "categorias.yaml")
    output_path = tmp_path / "sintetico.xlsx"

    warnings = write_sintetico_workbook(categorias_file, config_dir, data_dir, output_path)

    assert warnings == []
    wb = load_workbook(output_path)
    sheet = wb["INMS 1.4"]
    assert sheet.cell(row=2, column=1).value == (
        "Esse serviço não foi requisitado no período selecionado."
    )
