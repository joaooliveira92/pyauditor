import json
from pathlib import Path

from openpyxl import load_workbook

from pyauditor.cli.consolidate import run_consolidate
from pyauditor.cli.inms_grouped import (
    check_inms_grouped_ready,
    run_inms_grouped,
)
from pyauditor.cli.report import run_report
from pyauditor.excel.capa import (
    COMMON_FIELD_LABELS,
    ORGAO_FIELD_LABELS,
    bootstrap_capa_csv,
)

_ORGAOS = ('MinC', 'MTur')

# INMS 1.1: shape ratio, mode grupo_executor em duas categorias
# (ATENDIMENTO_N1 -> Grupo_executor "N1", OPERACAO_N3 -> qualquer coisa
# contendo "(CIT)") — o suficiente para exercitar o detalhamento por grupo
# executor real. Mesmo fixture de tests/test_cli_split.py.
_BASE_CONFIG_YAML = """\
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

_RAW_CSV = (
    'Nº Solicitacao;DataHoraFim;No prazo;Grupo_executor\n'
    '1;2026-06-01;S;N1\n'
    '2;2026-06-02;S;N1\n'
    '3;2026-06-03;S;(CIT) - Infra\n'
    '4;2026-06-04;N;(CIT) - Infra\n'
)


def _scaffold_capas(tmp_path: Path) -> None:
    bootstrap_capa_csv(tmp_path / 'capa.csv', COMMON_FIELD_LABELS)
    for orgao in _ORGAOS:
        bootstrap_capa_csv(tmp_path / f'capa_{orgao}.csv', ORGAO_FIELD_LABELS)


def _write_summary(
    roms_dir: Path,
    orgao: str,
    indicator_id: str,
    contractual_id: str,
    *,
    penalty_points: float = 0.0,
) -> None:
    target_dir = roms_dir / orgao / '2026-06'
    target_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        'indicator_id': indicator_id,
        'contractual_id': contractual_id,
        'name': f'Indicador {contractual_id}',
        'asset': None,
        'orgao': orgao,
        'shape': 'ratio',
        'target_operator': '>=',
        'target_value': 98.0,
        'result_pct': 97.71,
        'conforms': True,
        'penalty_points': penalty_points,
        'numerator': 171,
        'denominator': 175,
        'hard_failure': False,
    }
    (target_dir / f'{indicator_id}.json').write_text(
        json.dumps(summary), encoding='utf-8'
    )
    (target_dir / f'{indicator_id}.md').write_text('# ROM', encoding='utf-8')


def _build_consolidado(tmp_path: Path) -> None:
    """Precondição de `inms-grouped`: um `relatorio_2026-06_consolidado.xlsx`
    já publicado, com um INMS sem detalhamento (1.6, verbatim) e um INMS com
    detalhamento por grupo executor (1.1)."""
    _scaffold_capas(tmp_path)
    roms_dir = tmp_path / 'roms'
    for orgao in _ORGAOS:
        _write_summary(roms_dir, orgao, f'INMS-1.1-{orgao}', 'INMS 1.1')
        _write_summary(
            roms_dir, orgao, f'INMS-1.6-{orgao}', 'INMS 1.6',
            penalty_points=100.0,
        )
        exit_code = run_report(
            '2026-06',
            tmp_path / 'capa.csv',
            roms_dir / orgao,
            tmp_path / 'reports' / f'relatorio_2026-06_{orgao}.xlsx',
            config_dir=tmp_path / 'configs' / orgao,
            expected_orgao=orgao,
            data_dir=tmp_path,
        )
        assert exit_code.status == 'done'

    consolidate_result = run_consolidate(
        '2026-06',
        tmp_path / 'reports',
        roms_dir,
        tmp_path / 'reports' / 'relatorio_2026-06_consolidado.xlsx',
        data_dir=tmp_path,
    )
    assert consolidate_result.status == 'done'


def _write_grupo_executor_fixture(tmp_path: Path) -> None:
    """configs/CSV reais de INMS 1.1 para ambos os órgãos — o que
    `build_inms_grouped_workbook` recomputa do zero, independente do ROM."""
    shared = tmp_path / 'configs' / '_shared'
    shared.mkdir(parents=True, exist_ok=True)
    (shared / 'inms-01.yaml').write_text(_BASE_CONFIG_YAML, encoding='utf-8')

    for orgao in _ORGAOS:
        config_dir = tmp_path / 'configs' / orgao
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / 'categorias.yaml').write_text(
            _CATEGORIAS_YAML, encoding='utf-8'
        )
        data_dir = tmp_path / 'input' / orgao / '2026' / '06'
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / 'inms-01.csv').write_text(_RAW_CSV, encoding='utf-8')


def test_check_inms_grouped_ready_reports_missing_consolidado(
    tmp_path: Path,
) -> None:
    check = check_inms_grouped_ready('2026-06', tmp_path / 'reports')
    assert not check.satisfied
    assert 'relatorio_2026-06_consolidado.xlsx' in check.missing[0]


def test_run_inms_grouped_fails_when_consolidado_missing(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / 'reports' / 'planilha_inms_agrupada_2026-06.xlsx'
    result = run_inms_grouped(
        '2026-06',
        report_dir=tmp_path / 'reports',
        config_dir=tmp_path / 'configs',
        data_dir=tmp_path / 'input',
        output_path=output_path,
    )
    assert result.status == 'error'
    assert not result.output_path.exists()


def test_run_inms_grouped_builds_breakdown_and_verbatim_codes(
    tmp_path: Path,
) -> None:
    _build_consolidado(tmp_path)
    _write_grupo_executor_fixture(tmp_path)

    output_path = tmp_path / 'reports' / 'planilha_inms_agrupada_2026-06.xlsx'
    result = run_inms_grouped(
        '2026-06',
        report_dir=tmp_path / 'reports',
        config_dir=tmp_path / 'configs',
        data_dir=tmp_path / 'input',
        output_path=output_path,
    )

    assert result.status == 'done'
    assert result.breakdown_codes == ('1.1',)
    # INMS 1.1 (detalhado) + INMS 1.6 (verbatim).
    assert result.code_groups == 2
    assert output_path.exists()

    wb = load_workbook(output_path)
    ws = wb['INMS_BASE']

    codes = [ws.cell(r, 5).value for r in range(2, ws.max_row + 1)]
    assert 'INMS 1.01' in codes
    assert 'INMS 1.06' in codes

    # INMS 1.1: linhas "Consolidado"/"Consolidado - {órgão}" + detalhe por
    # grupo executor (N1, (CIT) - Infra), para os dois órgãos.
    labels_1_01 = [
        ws.cell(r, 2).value
        for r in range(2, ws.max_row + 1)
        if ws.cell(r, 5).value == 'INMS 1.01'
    ]
    assert 'Consolidado' in labels_1_01
    assert 'Consolidado - MinC' in labels_1_01
    assert 'Consolidado - MTur' in labels_1_01
    assert 'N1' in labels_1_01
    assert '(CIT) - Infra' in labels_1_01

    # INMS 1.6 nunca teve grupo_executor: as 2 linhas (uma por órgão) do
    # INMS_BASE oficial devem estar intactas, sem subtotal fabricado.
    rows_1_06 = [
        [ws.cell(r, c).value for c in range(1, 16)]
        for r in range(2, ws.max_row + 1)
        if ws.cell(r, 5).value == 'INMS 1.06'
    ]
    assert len(rows_1_06) == 2
    assert {row[6] for row in rows_1_06} == {'MinC', 'MTur'}

    # Nível 1 (mais recolhido): 1 linha visível por Código INMS.
    visible = [
        r for r in range(2, ws.max_row + 1) if not ws.row_dimensions[r].hidden
    ]
    assert len(visible) == 2
    outline_pr = ws.sheet_properties.outlinePr
    assert outline_pr is not None
    assert outline_pr.summaryBelow is False
