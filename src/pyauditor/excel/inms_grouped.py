"""`planilha_inms_agrupada_<competência>.xlsx` — uma visão do `INMS_BASE`
consolidado com agrupamento nativo de linhas do Excel (Dados > Agrupar),
substituindo o pooling por Nível (N1/N2/N3) por um detalhamento real em dois
grupos de INMS:

- Por Grupo executor, nos INMS com essa granularidade em `categorias.yaml`
  (hoje: 1.1, 1.2, 1.3, 1.7 — descoberto em runtime via `_grupo_detail_by_
  inms`, não hardcoded).
- Por ativo/sistema, nos INMS "por ativo" listados em
  `_PRECOMPUTED_BREAKDOWN_CODES` (hoje: 1.4, 1.5, 1.14 — hardcoded: outros
  INMS `precomputed_table` com a mesma forma, ex. 1.9/1.10/1.13, existem
  mas não foram pedidos).

Por que não é fabricação:
- Grupo executor: cada linha de detalhe roda
  `SHAPE_REGISTRY[shape].calculate()` (o mesmo motor de `measure`) sobre o
  subconjunto de linhas aceitas (pós quality-gate) de um único
  Grupo_executor — somar essas linhas por categoria reproduz exatamente o
  numerador/denominador já publicado no `INMS_BASE` oficial (conferido
  manualmente).
- Por ativo: cada linha do dataset bruto já É o resultado computado de um
  ativo (`numerator_column`/`denominator_column` do `calculation.
  precomputed_table`); somar essas duas colunas reproduz a mesma aritmética
  que `PrecomputedTableStrategy.calculate` já faz internamente para o
  `result_pct` agregado por órgão (também conferido manualmente contra o
  ROM publicado) — só que exposta por ativo em vez de só o agregado.

Em ambos os casos, "Consolidado - {órgão}" é o subtotal dos itens daquele
órgão; "Consolidado" (total geral, cruzando órgãos) só é gravado quando o
`shape` do indicador já é consolidável hoje (mesma regra de
`excel/orgao_consolidation.py`; ver `_CONSOLIDATABLE_SHAPES`) — `ratio`/
`segmented_ratio`/`count_difference` ganham essa linha, `precomputed_table`
nunca (a fórmula de pooling entre órgãos não é validada em nenhum outro
lugar do pipeline para esse shape), para nunca inventar um pooling que o
resto do pipeline não valida.

Grupos executores fora de `categorias.yaml` ("Grupo sob análise de
responsabilidade") ficam de fora do detalhamento por grupo: `measure`/
`report` nunca os soma na apuração oficial, incluí-los aqui infllaria os
subtotais silenciosamente.

Os INMS sem nenhum dos dois detalhamentos (a maioria — `whole_indicator` de
categoria única, ou `precomputed_table` sem essa granularidade pedida) são
copiados **verbatim** do `INMS_BASE` já publicado: nada é recalculado, nada
é fabricado para eles.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isnan
from pathlib import Path
from typing import Final, cast

import openpyxl
from openpyxl.styles import Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from pyauditor.categoria_filter import (
    GRUPO_EXECUTOR_COLUMN,
    base_config_stem,
    compute_categoria_values,
)
from pyauditor.cli.measure_inputs import resolve_measure_inputs
from pyauditor.codes import format_inms_code
from pyauditor.config.categorias import CategoriasFile, GrupoExecutorMode
from pyauditor.config.models import IndicatorConfig, PrecomputedTableCalculation
from pyauditor.config.niveis import NIVEL_BY_CATEGORIA
from pyauditor.config.resolution import per_orgao_paths
from pyauditor.engine.pipeline import measurement_source
from pyauditor.engine.quality_gates import QualityGateRunner
from pyauditor.engine.strategies import SHAPE_REGISTRY
from pyauditor.engine.strategies._numbers import parse_decimal
from pyauditor.engine.strategies._target import meets_target, safe_pct
from pyauditor.excel._style import (
    BODY_FONT,
    HEADER_FILL,
    HEADER_FONT,
    LABEL_FONT,
    CellValue,
)
from pyauditor.excel.inms_base import compliance_margin
from pyauditor.periodo import month_bounds

__all__: Final[tuple[str, ...]] = (
    'GroupedBuildResult',
    'build_inms_grouped_workbook',
)

_INMS_BASE_SHEET: Final[str] = 'INMS_BASE'
_ORGAOS: Final[tuple[str, ...]] = ('MinC', 'MTur')
_SEM_NIVEL: Final[str] = '—'
_AUDIT_REVIEW_LABEL: Final[str] = 'Grupo sob análise de responsabilidade'
_PERCENT_FMT: Final[str] = '0.00"%";(0.00"%");-'
# Mesma regra de `excel/orgao_consolidation.py` (constantes lá são privadas,
# não importáveis) — só grava "Consolidado" para shapes cujo pooling entre
# órgãos já é validado em outro lugar do pipeline.
_CONSOLIDATABLE_SHAPES: Final[frozenset[str]] = frozenset(
    {'ratio', 'segmented_ratio', 'count_difference'}
)
# INMS "por ativo" (`precomputed_table` com `numerator_column`/
# `denominator_column`/`name_column`) cujo detalhamento por ativo o usuário
# pediu explicitamente — mesma lista de `PER_ASSET_CONTRACTUAL_IDS` em
# `excel/orgao_consolidation.py`. Outros INMS `precomputed_table` com a
# mesma forma (1.9, 1.10, 1.13) existem mas não foram pedidos; ficam de
# fora até alguém pedir o mesmo tratamento para eles.
_PRECOMPUTED_BREAKDOWN_CODES: Final[frozenset[str]] = frozenset(
    {'1.4', '1.5', '1.14'}
)

_COLUMNS: Final[tuple[str, ...]] = (
    'Competência', 'Item contratual', 'Serviço', 'Grupo operacional',
    'Código INMS', 'Descrição', 'Órgão', 'Meta mínima ou máxima',
    'Sentido da meta', 'Numerador', 'Denominador', 'Resultado calculado',
    'Unidade', 'Conformidade', 'Diferença para a meta',
)
_COLUMN_WIDTHS: Final[dict[int, int]] = {
    1: 12, 2: 34, 3: 34, 4: 12, 5: 12, 6: 42, 7: 14, 8: 16, 9: 12,
    10: 12, 11: 12, 12: 16, 13: 10, 14: 14, 15: 16,
}
_TOP_BORDER: Final = Border(top=Side(style='thin', color='1F2937'))

# (categoria, nível, grupo executor, numerador, denominador)
type GrupoRow = tuple[str, str, str, float, float]


@dataclass(frozen=True, slots=True)
class _CodeInfo:
    target_value: float
    target_operator: str
    consolidatable: bool


@dataclass(frozen=True, slots=True)
class GroupedBuildResult:
    """Saída de `build_inms_grouped_workbook` — o workbook em memória mais
    as contagens que o comando de CLI reporta ao usuário."""

    workbook: openpyxl.Workbook
    code_groups: int
    org_subgroups: int
    total_rows: int
    breakdown_codes: tuple[str, ...]


def _compute_for_grupo(
    config: IndicatorConfig,
    id_column: str,
    rows_for_grupo: list[dict[str, str]],
) -> tuple[float, float]:
    """Roda o quality gate + a estratégia oficial (`SHAPE_REGISTRY`) sobre um
    único Grupo_executor — o mesmo caminho de `measure`, só que escopado."""
    gate_report = QualityGateRunner(
        config.quality_gates.checks, id_column=id_column
    ).run(rows_for_grupo)
    strategy = SHAPE_REGISTRY[config.calculation.shape]
    result = strategy.calculate(config, gate_report.accepted)
    numerator, denominator = strategy.pool_numerator_denominator(
        result.memoria
    )
    return numerator or 0.0, denominator or 0.0


def _is_subtotal_label(value: CellValue, *, prefix: str) -> bool:
    return isinstance(value, str) and value.startswith(prefix)


def _rows_for_grupo(
    rows: list[dict[str, str]], grupo: str
) -> list[dict[str, str]]:
    return [r for r in rows if r[GRUPO_EXECUTOR_COLUMN] == grupo]


def _grupo_detail_by_inms(
    competencia: str,
    config_dir: Path,
    data_dir: Path,
    scratch_dir: Path,
) -> tuple[dict[str, dict[str, list[GrupoRow]]], dict[str, _CodeInfo]]:
    """Para cada INMS com `mode: grupo_executor` em `categorias.yaml` (em
    qualquer um dos órgãos), devolve o detalhamento por grupo executor real,
    recomputado pelo motor oficial. `scratch_dir` só existe porque
    `resolve_measure_inputs` exige um destino gravável (`target_dir`) — este
    módulo nunca escreve ROM ali, é só leitura de configs/CSV.
    """
    rows_by_inms: dict[str, dict[str, list[GrupoRow]]] = {}
    info_by_inms: dict[str, _CodeInfo] = {}
    periodo = month_bounds(competencia)

    for orgao in _ORGAOS:
        paths = per_orgao_paths(
            config_dir=config_dir,
            data_dir=data_dir,
            output_dir=scratch_dir,
            orgao=orgao,
        )
        inputs, error = resolve_measure_inputs(
            competencia,
            paths.config_dir,
            paths.data_dir,
            paths.output_dir,
            expected_orgao=orgao,
            manifest=paths.manifest,
        )
        if error is not None or inputs is None:
            raise ValueError(f'{orgao}: {error}')

        configs_by_stem = {
            path.stem: (path, cfg) for path, _hash, cfg in inputs.configs
        }

        for inms_key, entries in inputs.per_inms.items():
            grupo_executor_entries = [
                (ck, e) for ck, e in entries if isinstance(e, GrupoExecutorMode)
            ]
            if not grupo_executor_entries:
                continue
            # `MeasureInputs.categorias_file` é `object | None` (assinatura
            # genérica) — não-None é garantido aqui porque `per_inms` (de
            # onde `entries` veio) só é populado junto com ele, na mesma
            # `_load_categorias`.
            categorias_file = inputs.categorias_file
            if not isinstance(categorias_file, CategoriasFile):
                raise ValueError(
                    f'{orgao}: categorias.yaml não carregado apesar de '
                    'per_inms não vazio'
                )

            stem = base_config_stem(inms_key)
            if stem not in configs_by_stem:
                continue
            config_path, config = configs_by_stem[stem]

            bundle = measurement_source(
                config,
                inputs.competencia_data_dir,
                paths.manifest,
                config_path=config_path,
                periodo=periodo,
                strict=False,
                emit_period_filter_logs=False,
            )
            if GRUPO_EXECUTOR_COLUMN not in bundle.fieldnames:
                continue

            real_values = {row[GRUPO_EXECUTOR_COLUMN] for row in bundle.rows}
            per_categoria_values, outros_values = compute_categoria_values(
                grupo_executor_entries, real_values
            )

            org_rows: list[GrupoRow] = []
            for categoria_key, effective_values in per_categoria_values.items():
                categoria = categorias_file.categorias[categoria_key]
                nivel = NIVEL_BY_CATEGORIA.get(categoria_key, _SEM_NIVEL)
                for grupo in sorted(effective_values):
                    num, den = _compute_for_grupo(
                        config,
                        config.source.id_column,
                        _rows_for_grupo(bundle.rows, grupo),
                    )
                    org_rows.append((categoria.label, nivel, grupo, num, den))

            for grupo in sorted(outros_values):
                num, den = _compute_for_grupo(
                    config,
                    config.source.id_column,
                    _rows_for_grupo(bundle.rows, grupo),
                )
                org_rows.append(
                    (_AUDIT_REVIEW_LABEL, _SEM_NIVEL, grupo, num, den)
                )

            rows_by_inms.setdefault(inms_key, {})[orgao] = org_rows
            if config.target is not None and inms_key not in info_by_inms:
                info_by_inms[inms_key] = _CodeInfo(
                    target_value=config.target.value,
                    target_operator=config.target.operator,
                    consolidatable=config.calculation.shape
                    in _CONSOLIDATABLE_SHAPES,
                )

    return rows_by_inms, info_by_inms


def _ativo_detail_by_inms(
    competencia: str,
    config_dir: Path,
    data_dir: Path,
    scratch_dir: Path,
) -> tuple[dict[str, dict[str, list[GrupoRow]]], dict[str, _CodeInfo]]:
    """Para os INMS "por ativo" em `_PRECOMPUTED_BREAKDOWN_CODES` (shape
    `precomputed_table` com `numerator_column`/`denominator_column`/
    `name_column` configurados), devolve o detalhamento por ativo/sistema:
    cada linha do dataset bruto já É o resultado computado de um ativo —
    somar `numerator_column`/`denominator_column` reproduz exatamente a
    mesma aritmética que `PrecomputedTableStrategy.calculate` já faz
    internamente para o `result_pct` agregado por órgão (conferido
    manualmente: bate com o ROM já publicado), só que exposta por ativo em
    vez de só o agregado — nada de quality-gate/estratégia para recomputar,
    é leitura + soma direta.

    Nunca consolidável entre órgãos (`consolidatable=False` sempre): mesma
    razão de `PER_ASSET_CONTRACTUAL_IDS` em `excel/orgao_consolidation.py`
    — a fórmula de pooling entre órgãos não é validada em nenhum outro
    lugar do pipeline para este shape.
    """
    rows_by_inms: dict[str, dict[str, list[GrupoRow]]] = {}
    info_by_inms: dict[str, _CodeInfo] = {}
    periodo = month_bounds(competencia)

    for orgao in _ORGAOS:
        paths = per_orgao_paths(
            config_dir=config_dir,
            data_dir=data_dir,
            output_dir=scratch_dir,
            orgao=orgao,
        )
        inputs, error = resolve_measure_inputs(
            competencia,
            paths.config_dir,
            paths.data_dir,
            paths.output_dir,
            expected_orgao=orgao,
            manifest=paths.manifest,
        )
        if error is not None or inputs is None:
            raise ValueError(f'{orgao}: {error}')

        configs_by_stem = {
            path.stem: (path, cfg) for path, _hash, cfg in inputs.configs
        }

        for inms_key in _PRECOMPUTED_BREAKDOWN_CODES:
            stem = base_config_stem(inms_key)
            if stem not in configs_by_stem:
                continue
            config_path, config = configs_by_stem[stem]
            calculation = config.calculation
            if not isinstance(calculation, PrecomputedTableCalculation):
                continue
            if (
                calculation.name_column is None
                or calculation.numerator_column is None
                or calculation.denominator_column is None
            ):
                continue

            bundle = measurement_source(
                config,
                inputs.competencia_data_dir,
                paths.manifest,
                config_path=config_path,
                periodo=periodo,
                strict=False,
                emit_period_filter_logs=False,
            )

            org_rows: list[GrupoRow] = []
            for row in bundle.rows:
                nome = row.get(calculation.name_column, '').strip()
                if not nome:
                    continue
                numerador = parse_decimal(
                    row.get(calculation.numerator_column, '') or ''
                )
                base = parse_decimal(
                    row.get(calculation.denominator_column, '') or ''
                )
                if isnan(numerador) or isnan(base):
                    continue
                org_rows.append(('', _SEM_NIVEL, nome, numerador, base))

            rows_by_inms.setdefault(inms_key, {})[orgao] = org_rows
            if config.target is not None and inms_key not in info_by_inms:
                info_by_inms[inms_key] = _CodeInfo(
                    target_value=config.target.value,
                    target_operator=config.target.operator,
                    consolidatable=False,
                )

    return rows_by_inms, info_by_inms


def _conformidade(
    resultado: float,
    denominador: float,
    target_value: float,
    target_operator: str,
) -> str:
    # Denominador 0 (sem atividade elegível no mês) não é falha de
    # performance — mesma leitura do `RatioStrategy` (0 ocorrências não é
    # 0% de conformidade).
    conforms = denominador == 0 or meets_target(
        resultado, target_operator, target_value
    )
    return 'Conforme' if conforms else 'Não conforme'


def _consolidado_row(
    competencia: str,
    label: str,
    orgao: str,
    inms_code: str,
    descricao: str | None,
    info: _CodeInfo,
    numerator: float,
    denominator: float,
) -> list[CellValue]:
    resultado = round(safe_pct(numerator, denominator), 2)
    conforme = _conformidade(
        resultado, denominator, info.target_value, info.target_operator
    )
    diff = compliance_margin(resultado, info.target_value, info.target_operator)
    return [
        competencia, label, None, None, inms_code, descricao, orgao,
        info.target_value, info.target_operator, numerator, denominator,
        resultado, '%', conforme, round(diff, 2) if diff is not None else None,
    ]


def _build_breakdown_rows(
    competencia: str,
    rows_by_inms: dict[str, dict[str, list[GrupoRow]]],
    info_by_inms: dict[str, _CodeInfo],
    descricao_by_inms: dict[str, str | None],
) -> dict[str, list[list[CellValue]]]:
    """Monta as linhas finais (detalhe + subtotal por órgão + total geral,
    quando consolidável) de cada INMS com detalhamento por grupo executor."""
    rows_by_code: dict[str, list[list[CellValue]]] = {}

    for inms_key, by_orgao in rows_by_inms.items():
        info = info_by_inms.get(inms_key)
        if info is None:
            continue
        inms_code = format_inms_code(f'INMS {inms_key}')
        descricao = descricao_by_inms.get(inms_key)

        code_rows: list[list[CellValue]] = []
        org_subtotals: list[tuple[str, float, float]] = []

        for orgao in _ORGAOS:
            org_rows = [
                row for row in by_orgao.get(orgao, [])
                if row[0] != _AUDIT_REVIEW_LABEL
            ]
            org_num = sum(n for _, _, _, n, _ in org_rows)
            org_den = sum(d for _, _, _, _, d in org_rows)
            org_subtotals.append((orgao, org_num, org_den))
            if not org_rows:
                continue

            detail_rows: list[list[CellValue]] = []
            for categoria_label, nivel, grupo, num, den in org_rows:
                resultado = round(safe_pct(num, den), 2)
                conforme = _conformidade(
                    resultado, den, info.target_value, info.target_operator
                )
                diff = compliance_margin(
                    resultado, info.target_value, info.target_operator
                )
                detail_rows.append([
                    competencia, grupo, categoria_label, nivel, inms_code,
                    descricao, orgao, info.target_value, info.target_operator,
                    num, den, resultado, '%', conforme,
                    round(diff, 2) if diff is not None else None,
                ])

            code_rows.append(_consolidado_row(
                competencia, f'Consolidado - {orgao}', orgao, inms_code,
                descricao, info, org_num, org_den,
            ))
            code_rows.extend(detail_rows)

        if info.consolidatable:
            grand_num = sum(n for _, n, _ in org_subtotals)
            grand_den = sum(d for _, _, d in org_subtotals)
            code_rows.insert(0, _consolidado_row(
                competencia, 'Consolidado', 'Consolidado', inms_code,
                descricao, info, grand_num, grand_den,
            ))

        if code_rows:
            rows_by_code[inms_key] = code_rows

    return rows_by_code


def _existing_rows_by_code(ws: Worksheet) -> dict[str, list[list[CellValue]]]:
    """Linhas do `INMS_BASE` já publicado, por Código INMS — a fonte
    verbatim para os indicadores sem detalhamento por grupo executor."""
    by_code: dict[str, list[list[CellValue]]] = {}
    for r in range(2, ws.max_row + 1):
        code = ws.cell(r, 5).value
        if code is None:
            continue
        # `Cell.value` is typed against every openpyxl-representable scalar
        # (Decimal, datetime, ...); `_new_sheet`/`write_row` (`_style.py`)
        # only ever write `CellValue`s, so this narrowing is safe for a
        # workbook this pipeline generated itself.
        row_values = cast(
            'list[CellValue]',
            [ws.cell(r, c).value for c in range(1, 16)],
        )
        by_code.setdefault(str(code), []).append(row_values)
    return by_code


def _write_rows(ws: Worksheet, final_rows: list[list[CellValue]]) -> None:
    for row_idx, values in enumerate(final_rows, start=2):
        label = values[1]
        is_subtotal = _is_subtotal_label(label, prefix='Consolidado')
        for c, v in enumerate(values, start=1):
            cell = ws.cell(row_idx, c, v)
            cell.font = LABEL_FONT if is_subtotal else BODY_FONT
            if c in (8, 12, 15) and isinstance(v, int | float):
                cell.number_format = _PERCENT_FMT
        if is_subtotal:
            for c in range(1, len(_COLUMNS) + 1):
                ws.cell(row_idx, c).border = _TOP_BORDER


def _apply_breakdown_outline(
    ws: Worksheet, r: int, block: list[list[CellValue]]
) -> int:
    """Agrupamento de um bloco com detalhamento. Cada linha-cabeçalho é
    identificada pelo rótulo `Consolidado`/`Consolidado - {órgão}`; a
    primeira do bloco é o nível 0 — o total geral, quando o shape é
    consolidável entre órgãos (`_CodeInfo.consolidatable`), senão o
    primeiro subtotal por órgão já assume esse papel (shapes como
    `precomputed_table`, onde não existe pooling entre órgãos validado —
    ver `_CONSOLIDATABLE_SHAPES`). Cabeçalhos seguintes são nível 1; suas
    linhas de detalhe, nível 2. Devolve a quantidade de subgrupos (nível 1)
    criados."""
    n = len(block)
    n_subgroups = 0
    offset = 0
    first = True
    while offset < n:
        header_row = r + offset
        level = 0 if first else 1
        ws.row_dimensions[header_row].outlineLevel = level
        ws.row_dimensions[header_row].hidden = not first
        if not first:
            n_subgroups += 1
        offset += 1
        detail_start = offset
        while offset < n and not _is_subtotal_label(
            block[offset][1], prefix='Consolidado'
        ):
            ws.row_dimensions[r + offset].outlineLevel = 2
            ws.row_dimensions[r + offset].hidden = True
            offset += 1
        if offset > detail_start:
            ws.row_dimensions[header_row].collapsed = True
        first = False
    if n > 1:
        ws.row_dimensions[r].collapsed = True
    return n_subgroups


def _apply_outline(
    ws: Worksheet,
    code_blocks: list[tuple[str, list[list[CellValue]]]],
    breakdown_codes: frozenset[str],
) -> int:
    """Agrupamento nativo em 3 níveis: nível 0 = 1 linha por Código INMS;
    nível 1 = subtotal por órgão ("Consolidado - {órgão}" ou a linha
    existente); nível 2 = detalhe. `summaryBelow=False` (setado pelo
    chamador) mantém a linha-resumo acima do seu detalhe. Devolve a
    quantidade de subgrupos (nível 1) criados."""
    r = 2
    n_org_subgroups = 0
    for code_full, block in code_blocks:
        n = len(block)
        inms_key = code_full.replace('INMS ', '')
        if inms_key in breakdown_codes:
            n_org_subgroups += _apply_breakdown_outline(ws, r, block)
        else:
            orgs_seen: list[CellValue] = []
            for offset in range(n):
                orgao_val = block[offset][6]
                row_i = r + offset
                if orgao_val not in orgs_seen:
                    orgs_seen.append(orgao_val)
                    level = 0 if offset == 0 else 1
                    ws.row_dimensions[row_i].outlineLevel = level
                    ws.row_dimensions[row_i].hidden = level != 0
                    if level == 0:
                        ws.row_dimensions[row_i].collapsed = len(orgs_seen) < n
                    n_org_subgroups += 1
                else:
                    ws.row_dimensions[row_i].outlineLevel = 2
                    ws.row_dimensions[row_i].hidden = True
        r += n
    return n_org_subgroups


def build_inms_grouped_workbook(
    competencia: str,
    consolidado_path: Path,
    config_dir: Path,
    data_dir: Path,
    scratch_dir: Path,
) -> GroupedBuildResult:
    """Monta o workbook completo (in-memory, o chamador grava). Requer que
    `consolidado_path` (o `relatorio_<competência>_consolidado.xlsx` do
    `consolidate`) já exista — a fonte dos 10 INMS sem detalhamento por
    grupo executor e da Descrição de cada código.

    Raises:
        FileNotFoundError: se `consolidado_path` não existe.
        ValueError: se `INMS_BASE` estiver ausente/vazia, ou se
            `resolve_measure_inputs` falhar para um dos órgãos.
    """
    if not consolidado_path.is_file():
        raise FileNotFoundError(
            f'{consolidado_path} não existe — rode `pyauditor consolidate '
            f'{competencia}` antes'
        )

    wb_src = openpyxl.load_workbook(consolidado_path)
    if _INMS_BASE_SHEET not in wb_src.sheetnames:
        raise ValueError(
            f'{consolidado_path}: aba {_INMS_BASE_SHEET!r} ausente'
        )
    existing_by_code = _existing_rows_by_code(wb_src[_INMS_BASE_SHEET])
    if not existing_by_code:
        raise ValueError(f'{consolidado_path}: {_INMS_BASE_SHEET} sem linhas')

    rows_by_inms, info_by_inms = _grupo_detail_by_inms(
        competencia, config_dir, data_dir, scratch_dir
    )
    ativo_rows_by_inms, ativo_info_by_inms = _ativo_detail_by_inms(
        competencia, config_dir, data_dir, scratch_dir
    )
    # Chaves disjuntas por construção (grupo executor vs. `_PRECOMPUTED_
    # BREAKDOWN_CODES`) — `update` nunca sobrescreve um INMS já presente.
    rows_by_inms.update(ativo_rows_by_inms)
    info_by_inms.update(ativo_info_by_inms)

    descricao_by_inms: dict[str, str | None] = {}
    for inms_key in rows_by_inms:
        code_full = format_inms_code(f'INMS {inms_key}')
        existing_rows = existing_by_code.get(code_full, [])
        descricao = existing_rows[0][5] if existing_rows else None
        descricao_by_inms[inms_key] = (
            descricao if isinstance(descricao, str) else None
        )

    breakdown_rows_by_code = _build_breakdown_rows(
        competencia, rows_by_inms, info_by_inms, descricao_by_inms
    )
    breakdown_by_padded = {
        format_inms_code(f'INMS {k}').replace('INMS ', ''): v
        for k, v in breakdown_rows_by_code.items()
    }

    all_codes = sorted(
        existing_by_code, key=lambda c: float(c.replace('INMS ', ''))
    )
    final_rows: list[list[CellValue]] = []
    code_blocks: list[tuple[str, list[list[CellValue]]]] = []
    for code_full in all_codes:
        inms_key = code_full.replace('INMS ', '')
        block = breakdown_by_padded.get(inms_key, existing_by_code[code_full])
        code_blocks.append((code_full, block))
        final_rows.extend(block)

    wb = openpyxl.Workbook()
    default_sheet = wb.active
    if default_sheet is None:
        raise RuntimeError('workbook novo sem aba ativa (openpyxl)')
    wb.remove(default_sheet)
    ws = wb.create_sheet(_INMS_BASE_SHEET)
    ws.sheet_view.showGridLines = False

    for c, name in enumerate(_COLUMNS, start=1):
        cell = ws.cell(1, c, name)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
    for c, width in _COLUMN_WIDTHS.items():
        ws.column_dimensions[get_column_letter(c)].width = width

    _write_rows(ws, final_rows)
    n_org_subgroups = _apply_outline(
        ws, code_blocks, frozenset(breakdown_by_padded)
    )

    ws.row_dimensions[1].outlineLevel = 0
    ws.row_dimensions[1].hidden = False
    ws.sheet_properties.outlinePr.summaryBelow = False
    ws.sheet_properties.outlinePr.summaryRight = False
    ws.sheet_view.showOutlineSymbols = True

    return GroupedBuildResult(
        workbook=wb,
        code_groups=len(code_blocks),
        org_subgroups=n_org_subgroups,
        total_rows=len(final_rows),
        breakdown_codes=tuple(sorted(breakdown_rows_by_code, key=float)),
    )
