"""Caracterização da aba enriquecida do INMS 1.1 (`inms_1_1_audit.write_sheet`),
acionada por `sintetico.py` quando o CSV bruto tem as colunas de detalhe
(`Nº Solicitacao`, `Atividades`, `DataHoraLimite`, `TecnicoExecutor`). Sem
isso, nenhum teste do repositório passava pelo caminho enriquecido — só o
renderer genérico (`test_excel_sintetico.py`). Estes testes fixam o
comportamento observável (estrutura de seções, fórmulas-chave) para permitir
refatoração segura de `inms_1_1_audit.py`.
"""

from datetime import date
from pathlib import Path

from openpyxl import load_workbook

from pyauditor.config.categorias import load_categorias
from pyauditor.excel.sintetico import write_sintetico_workbook
from pyauditor.periodo import PeriodoAfericao

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
"""

# Todas as colunas exigidas por `inms_1_1_audit.has_required_columns`, ao
# contrário da fixture minimalista de `test_excel_sintetico.py`.
_INMS_01_RAW_CSV_ENRIQUECIDO = (
    "Nº Solicitacao;Atividades;DataHoraSolicitacao;DataHoraLimite;DataHoraFim;"
    "No prazo;Grupo_executor;TecnicoExecutor\n"
    "1;Reset de senha;01/06/2026 08:00;01/06/2026 10:00;01/06/2026 09:30;"
    "S;N1;Fulano\n"
    "2;Instalação de software;01/06/2026 09:00;01/06/2026 11:00;02/06/2026 09:00;"
    "N;N1;Fulano\n"
    "3;Acesso a sistema;01/06/2026 08:00;01/06/2026 10:00;01/06/2026 09:00;"
    "S;N2;Beltrano\n"
    "4;Restart de serviço;01/06/2026 08:00;01/06/2026 10:00;01/06/2026 20:00;"
    "S;(CIT) - Infra;Ciclano\n"
)


def _write_fixture(tmp_path: Path) -> tuple[Path, Path]:
    config_dir = tmp_path / "configs"
    data_dir = tmp_path / "input" / "2026" / "06"
    config_dir.mkdir(parents=True)
    data_dir.mkdir(parents=True)

    (config_dir / "inms-01.yaml").write_text(_INMS_01_CONFIG, encoding="utf-8")
    (config_dir / "categorias.yaml").write_text(_CATEGORIAS_YAML, encoding="utf-8")
    (data_dir / "inms-01.csv").write_text(_INMS_01_RAW_CSV_ENRIQUECIDO, encoding="utf-8")

    return config_dir, data_dir


def test_enriched_sheet_is_used_when_raw_csv_has_detail_columns(tmp_path: Path) -> None:
    config_dir, data_dir = _write_fixture(tmp_path)
    categorias_file = load_categorias(config_dir / "categorias.yaml")
    output_path = tmp_path / "sintetico.xlsx"
    periodo = PeriodoAfericao(date(2026, 6, 1), date(2026, 6, 30))

    warnings = write_sintetico_workbook(
        categorias_file, config_dir, data_dir, output_path, periodo=periodo
    )

    assert warnings == []
    wb = load_workbook(output_path)
    sheet = wb["INMS 1.1"]

    assert sheet["A1"].value == "INMS 1.1 – Incidentes atendidos dentro do prazo"

    section_bars = {
        cell.value
        for row in sheet.iter_rows(min_col=1, max_col=1)
        for cell in row
        if isinstance(cell.value, str) and cell.value.startswith("SEÇÃO")
    }
    assert section_bars == {
        "SEÇÃO 1 · IDENTIFICAÇÃO",
        "SEÇÃO 2 · RESUMO EXECUTIVO",
        "SEÇÃO 3 · MEMÓRIA DO CÁLCULO CONSOLIDADO",
        "SEÇÃO 4 · DETALHAMENTO POR GRUPO EXECUTOR",
        "SEÇÃO 5 · SUBTOTAIS POR NÍVEL (informação gerencial)",
        "SEÇÃO 6 · INCIDENTES FORA DO PRAZO",
        "SEÇÃO 7 · AUDITORIA DO PRAZO CONTRATUAL",
        "SEÇÃO 8 · TEMPO CORRIDO MÉDIO ATÉ A RESOLUÇÃO",
        "SEÇÃO 9 · PENALIDADE (CÁLCULO PRELIMINAR)",
    }

    # Seção 2 — resumo executivo: fórmulas dependem só da base de apoio.
    assert sheet["A13"].value == "=0.98"
    assert sheet["B13"].value == "=COUNTA($R$2:$R$5)"
    assert sheet["C13"].value == '=COUNTIF($X$2:$X$5,"S")'
    assert sheet["D13"].value == '=COUNTIF($X$2:$X$5,"N")'
    assert sheet["E13"].value == "=C13/B13"

    # Seção 4 — uma linha por grupo executor real do CSV.
    grupo_col = [cell.value for cell in sheet["C"][29:32]]
    assert grupo_col == ["N1", "N2", "(CIT) - Infra"]

    # Base de apoio (colunas R:AM) tem uma linha por incidente do CSV bruto.
    assert sheet["R2"].value == "1"
    assert sheet["R5"].value == "4"


def test_enriched_sheet_lists_out_of_deadline_incidents_in_section_6(
    tmp_path: Path,
) -> None:
    config_dir, data_dir = _write_fixture(tmp_path)
    categorias_file = load_categorias(config_dir / "categorias.yaml")
    output_path = tmp_path / "sintetico.xlsx"
    periodo = PeriodoAfericao(date(2026, 6, 1), date(2026, 6, 30))

    write_sintetico_workbook(
        categorias_file, config_dir, data_dir, output_path, periodo=periodo
    )

    wb = load_workbook(output_path)
    sheet = wb["INMS 1.1"]

    s6_bar_row = next(
        cell.row
        for row in sheet.iter_rows(min_col=1, max_col=1)
        for cell in row
        if cell.value == "SEÇÃO 6 · INCIDENTES FORA DO PRAZO"
    )
    header_row = s6_bar_row + 1
    assert sheet.cell(row=header_row, column=1).value == "Nº solicitação"
    first_data_row = header_row + 1
    assert sheet.cell(row=first_data_row, column=1).value == (
        '=IFERROR(INDEX($R$2:$R$5,MATCH(1,$AH$2:$AH$5,0)),"")'
    )
