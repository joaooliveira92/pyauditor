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
    assert sheet["E13"].value == '=IF(B13=0,"Sem ocorrências",C13/B13)'

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


def test_enriched_sheet_sanitizes_formula_injection_from_raw_csv(tmp_path: Path) -> None:
    config_dir, data_dir = _write_fixture(tmp_path)
    malicious_csv = (
        "Nº Solicitacao;Atividades;DataHoraSolicitacao;DataHoraLimite;DataHoraFim;"
        "No prazo;Grupo_executor;TecnicoExecutor\n"
        '=HYPERLINK("https://exemplo.invalid","clique");'
        "+Atividade maliciosa;01/06/2026 08:00;01/06/2026 10:00;01/06/2026 09:30;"
        "S;N1;-Fulano\n"
    )
    (data_dir / "inms-01.csv").write_text(malicious_csv, encoding="utf-8")
    categorias_file = load_categorias(config_dir / "categorias.yaml")
    output_path = tmp_path / "sintetico.xlsx"
    periodo = PeriodoAfericao(date(2026, 6, 1), date(2026, 6, 30))

    write_sintetico_workbook(
        categorias_file, config_dir, data_dir, output_path, periodo=periodo
    )

    wb = load_workbook(output_path)
    sheet = wb["INMS 1.1"]

    # Coluna de apoio: valores maliciosos gravados como texto literal
    # (prefixados com apóstrofo), não interpretados como fórmula.
    assert sheet["R2"].value == '\'=HYPERLINK("https://exemplo.invalid","clique")'
    assert sheet["T2"].value == "'+Atividade maliciosa"
    assert sheet["Y2"].value == "'-Fulano"


def test_enriched_sheet_flags_invalid_and_inconsistent_dates(tmp_path: Path) -> None:
    config_dir, data_dir = _write_fixture(tmp_path)
    csv_with_bad_dates = (
        "Nº Solicitacao;Atividades;DataHoraSolicitacao;DataHoraLimite;DataHoraFim;"
        "No prazo;Grupo_executor;TecnicoExecutor\n"
        # Linha 2: data de abertura malformada.
        "1;Reset de senha;31/02/2026 08:00;01/06/2026 10:00;01/06/2026 09:30;S;N1;Fulano\n"
        # Linha 3: data de encerramento vazia (incidente ainda em aberto) — OK.
        "2;Instalação;01/06/2026 08:00;01/06/2026 10:00;;S;N1;Fulano\n"
        # Linha 4: encerramento anterior à abertura.
        "3;Restart;01/06/2026 12:00;01/06/2026 14:00;01/06/2026 10:00;N;N1;Fulano\n"
        # Linha 5: tudo válido.
        "4;Acesso;01/06/2026 08:00;01/06/2026 10:00;01/06/2026 09:00;S;N1;Fulano\n"
    )
    (data_dir / "inms-01.csv").write_text(csv_with_bad_dates, encoding="utf-8")
    categorias_file = load_categorias(config_dir / "categorias.yaml")
    output_path = tmp_path / "sintetico.xlsx"
    periodo = PeriodoAfericao(date(2026, 6, 1), date(2026, 6, 30))

    write_sintetico_workbook(
        categorias_file, config_dir, data_dir, output_path, periodo=periodo
    )

    wb = load_workbook(output_path)
    sheet = wb["INMS 1.1"]

    # Coluna AJ (situação dos dados).
    assert sheet["AJ2"].value == "Data de abertura inválida"
    assert sheet["AJ3"].value == "OK"
    assert sheet["AJ4"].value == "Encerramento anterior à abertura"
    assert sheet["AJ5"].value == "OK"

    # U2 vazia (data de abertura malformada -> não gravada) protege AB2/AG2
    # contra tratar célula vazia como zero.
    assert sheet["U2"].value is None
    assert sheet["AB2"].value == '=IF(U2="","",U2+2.0/24)'
    assert sheet["AG2"].value == '=IF(OR(U2="",W2="",W2<U2),"",W2-U2)'

    # Linha 4: encerramento < abertura -> AG fica vazio, não negativo.
    assert sheet["AG4"].value == '=IF(OR(U4="",W4="",W4<U4),"",W4-U4)'


def test_prazo_tolerancia_minutos_used_consistently(tmp_path: Path) -> None:
    from pyauditor.excel._datetime import PRAZO_TOLERANCIA_MINUTOS

    config_dir, data_dir = _write_fixture(tmp_path)
    categorias_file = load_categorias(config_dir / "categorias.yaml")
    output_path = tmp_path / "sintetico.xlsx"
    periodo = PeriodoAfericao(date(2026, 6, 1), date(2026, 6, 30))

    write_sintetico_workbook(
        categorias_file, config_dir, data_dir, output_path, periodo=periodo
    )

    wb = load_workbook(output_path)
    sheet = wb["INMS 1.1"]

    # Coluna AC (divergência de prazo) usa a mesma constante de tolerância
    # que o cálculo Python da amostra da Seção 7 — sem valor duplicado.
    assert f"{PRAZO_TOLERANCIA_MINUTOS}/1440" in sheet["AC2"].value


def test_zero_denominator_formulas_are_guarded_against_div0(tmp_path: Path) -> None:
    """A-01: nenhuma fórmula que divide por B13 (IAP) ou pelo total de linhas
    da Seção 5 pode gerar #DIV/0! quando o denominador for zero — todas devem
    ter guarda explícita ("Sem ocorrências"/"Não aplicável")."""
    config_dir, data_dir = _write_fixture(tmp_path)
    categorias_file = load_categorias(config_dir / "categorias.yaml")
    output_path = tmp_path / "sintetico.xlsx"
    periodo = PeriodoAfericao(date(2026, 6, 1), date(2026, 6, 30))

    write_sintetico_workbook(
        categorias_file, config_dir, data_dir, output_path, periodo=periodo
    )

    wb = load_workbook(output_path)
    sheet = wb["INMS 1.1"]

    def formula(coord: str) -> str:
        value = sheet[coord].value
        assert isinstance(value, str)
        return value

    # Seção 2.
    assert 'IF(B13=0,"Sem ocorrências"' in formula("E13")
    assert 'IF(B13=0,""' in formula("F13")
    assert 'IF(B13=0,"Sem ocorrências"' in formula("G13")

    # Seção 3.
    assert 'IF(B13=0,""' in formula("B23")

    # Seção 5 — linha "Total geral" (label fixo) e verificação cruzada.
    total_row = next(
        cell.row
        for row in sheet.iter_rows(min_col=1, max_col=1)
        for cell in row
        if cell.value == "Total geral"
    )
    assert 'IF(B' in formula(f"E{total_row}") and "Sem ocorrências" in formula(f"E{total_row}")
    check_label_row = next(
        cell.row
        for row in sheet.iter_rows(min_col=1, max_col=1)
        for cell in row
        if cell.value == "Verificação cruzada (Seção 5 = Seção 2/3):"
    )
    assert "ISNUMBER" in formula(f"B{check_label_row}")

    # Seção 7 — três metodologias de controle e % de divergência.
    controles_row = next(
        cell.row
        for row in sheet.iter_rows(min_col=1, max_col=1)
        for cell in row
        if cell.value == "Controles de resultado"
    )
    for offset in range(2, 5):
        r = controles_row + offset
        assert 'IF(B13=0,"Sem ocorrências"' in formula(f"B{r}")
        assert 'IF(B13=0,"Não aplicável"' in formula(f"C{r}")
    divergentes_label_row = next(
        cell.row
        for row in sheet.iter_rows(min_col=1, max_col=1)
        for cell in row
        if cell.value == "Registros com limite divergente:"
    )
    assert 'IF(B13=0,"Sem ocorrências"' in formula(f"D{divergentes_label_row}")

    # Seção 9 — penalidade não pode ser calculada como se a meta tivesse
    # sido descumprida quando não há incidentes.
    penalidade_base_row = next(
        cell.row
        for row in sheet.iter_rows(min_col=1, max_col=1)
        for cell in row
        if cell.value == "Penalidade-base:"
    )
    assert 'IF(B13=0,"Não aplicável"' in formula(f"B{penalidade_base_row}")


def test_section_3_narrativa_reflects_actual_margin_sign(tmp_path: Path) -> None:
    """A-02: a narrativa da Seção 3 (célula A26) não pode dizer "abaixo do
    mínimo" quando a meta foi superada."""
    config_dir, data_dir = _write_fixture(tmp_path)
    categorias_file = load_categorias(config_dir / "categorias.yaml")
    output_path = tmp_path / "sintetico.xlsx"
    periodo = PeriodoAfericao(date(2026, 6, 1), date(2026, 6, 30))

    write_sintetico_workbook(
        categorias_file, config_dir, data_dir, output_path, periodo=periodo
    )

    wb = load_workbook(output_path)
    sheet = wb["INMS 1.1"]
    formula = sheet["A26"].value
    assert isinstance(formula, str)

    assert formula.startswith(
        '=IF(B13=0,"Sem incidentes abertos no período — indicador não mensurável.",'
    )
    assert "IF(B25<0,CONCATENATE(" in formula
    assert "IF(B25=0,CONCATENATE(" in formula
    # As três narrativas (abaixo/exato/acima) coexistem na fórmula, cada uma
    # sob a guarda IF correta — não há mais um único texto fixo com ABS().
    assert 'ABS(B25)," incidente(s) abaixo do mínimo necessário."' in formula
    assert 'exatamente no mínimo necessário."' in formula
    assert '",B25," incidente(s) acima do mínimo necessário."' in formula
    assert formula.count("CONCATENATE(") == 3
