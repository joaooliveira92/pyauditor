"""Decide e executa o renderer de uma única aba de INMS — a única
responsabilidade deste módulo. Carrega a config base, resolve o dataset via
`measurement_source` e escolhe entre os renderers por-shape de `_sheets/`
(inclusive a aba enriquecida do INMS 1.1) conforme o `calculation`/colunas
do config, sem afetar as demais abas do workbook quando algo falha aqui —
todo erro específico deste INMS vira warning devolvido ao chamador."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Final

from openpyxl import Workbook

from pyauditor.categoria_filter import GRUPO_EXECUTOR_COLUMN, base_config_stem
from pyauditor.config.categorias import (
    CategoriasFile,
    GrupoExecutorMode,
    WholeIndicatorMode,
)
from pyauditor.config.manifest import DatasetManifest
from pyauditor.config.models import (
    ColumnContains,
    ColumnEquals,
    IndicatorConfig,
    PrecomputedTableCalculation,
    RatioCalculation,
    SegmentedRatioCalculation,
)
from pyauditor.engine.pipeline import measurement_source
from pyauditor.excel import inms_1_1_audit
from pyauditor.excel.inms_1_2 import write as inms_1_2_write
from pyauditor.excel.inms_1_2._layout import CategoryParams
from pyauditor.excel.inms_1_3 import write as inms_1_3_write
from pyauditor.excel.sintetico._sheets.grupo_executor import (
    _write_grupo_executor_sheet,
    _write_whole_indicator_sheet,
)
from pyauditor.excel.sintetico._sheets.nao_ativado import (
    _write_nao_ativado_sheet,
)
from pyauditor.excel.sintetico._sheets.precomputed import (
    _write_precomputed_table_sheet,
)
from pyauditor.excel.sintetico._sheets.precomputed_audit import (
    _write_precomputed_audit_sheet,
)
from pyauditor.excel.sintetico._sheets.ratio_aggregate import (
    _write_ratio_aggregate_sheet,
)
from pyauditor.excel.sintetico._sheets.ratio_audit import (
    _write_ratio_audit_sheet,
)
from pyauditor.periodo import PeriodoAfericao

from ._config import load_base_config
from ._types import (
    _INMS_1_1,
    _INMS_1_2,
    _INMS_1_3,
    _INMS_1_7,
    _INMS_1_11,
    _INMS_1_12,
    InmsEntries,
)

_RATIO_AUDIT_INMS_KEYS: Final[frozenset[str]] = frozenset(
    {_INMS_1_7, _INMS_1_11, _INMS_1_12}
)


def _segmented_ratio_category_params(
    calculation: SegmentedRatioCalculation,
) -> list[CategoryParams] | None:
    """`None` quando alguma categoria não segue o vocabulário assumido pela
    aba enriquecida do INMS 1.2 (denominador por `ColumnContains`,
    numerador `No prazo == S`) — degrada para o renderer genérico em vez de
    hardcodar uma suposição que só é verdadeira para a config real de hoje."""
    params: list[CategoryParams] = []
    for category in calculation.categories:
        if not isinstance(category.denominator_filter, ColumnContains):
            return None
        if (
            not isinstance(category.numerator_filter, ColumnEquals)
            or category.numerator_filter.equals != 'S'
        ):
            return None
        params.append(
            CategoryParams(
                label=category.name,
                sla_contains=category.denominator_filter.contains,
                step_points=category.step_points,
            )
        )
    return params


def _ratio_count_distinct_eligible(
    inms_key: str, base_config: IndicatorConfig
) -> bool:
    """INMS 1.7/1.11/1.12 (`ratio`/`count_distinct` sem coluna "No
    prazo"/`DataHoraFim` — satisfação, telefonia) usam o renderer
    enriquecido (`ratio_audit.py`), que conta o critério real
    (`numerator_filter`/`denominator_filter`, o mesmo predicado de
    `RatioStrategy._aggregate`) em vez do genérico que assume essas colunas
    e só produzia traços. Gate por `inms_key` explícito, não só pelo shape
    — `ratio`/`count_distinct` é o mesmo shape do INMS 1.1 (que tem sua
    própria aba bespoke) e de fixtures de teste do renderer genérico."""
    calc = base_config.calculation
    return (
        inms_key in _RATIO_AUDIT_INMS_KEYS
        and isinstance(calc, RatioCalculation)
        and calc.aggregation == 'count_distinct'
        and base_config.target is not None
        and base_config.penalty is not None
        and bool(base_config.scope.contract)
    )


def render_inms_sheet(
    workbook: Workbook,
    inms_key: str,
    entries: InmsEntries,
    categorias_file: CategoriasFile,
    config_dir: Path,
    competencia_data_dir: Path,
    manifest: DatasetManifest | None,
    periodo: PeriodoAfericao | None,
    strict: bool,
    orgao: str,
    generated_at: datetime,
) -> list[str]:
    """Adiciona a aba `INMS {inms_key}` a `workbook` (ou degrada para
    'não ativado'/warning). Nunca lança — todo problema específico deste
    INMS vira warning na lista devolvida."""
    warnings: list[str] = []
    sheet_name = f'INMS {inms_key}'

    try:
        base_config = load_base_config(inms_key, config_dir, orgao)
    except (OSError, ValueError) as exc:
        warnings.append(
            f'sintetico.xlsx:INMS{inms_key}:falhaaocarregarconfigbase:{exc}'
        )
        return warnings

    # Backbone (ticket 03): resolve→valida→lê→filtra→gates, um só lugar
    # para os quatro reimplementadores do pipeline de medição. Sintetico
    # nunca emite WARN de janela vazia (a mesma passada do bruto coube
    # ao split) — `emit_period_filter_logs=False`. `period_column`
    # ausente/não presente no header é erro acionável (spec §2 ponto 1,
    # issue 01 item 5) — degrada esta aba como os demais erros do loop.
    try:
        bundle = measurement_source(
            base_config,
            competencia_data_dir,
            manifest,
            config_path=config_dir / f'{base_config_stem(inms_key)}.yaml',
            periodo=periodo,
            strict=strict,
            emit_period_filter_logs=False,
        )
    except FileNotFoundError:
        _write_nao_ativado_sheet(workbook, sheet_name)
        return warnings
    except (OSError, ValueError) as exc:
        warnings.append(f'sintetico.xlsx: INMS {inms_key}: {exc}')
        return warnings

    raw_csv_path = bundle.csv_path
    fieldnames = bundle.fieldnames
    rows = bundle.rows
    accepted_ids = bundle.accepted_ids

    whole_indicator_entries = [
        (ck, e) for ck, e in entries if isinstance(e, WholeIndicatorMode)
    ]

    grupo_executor_entries = [
        (ck, e) for ck, e in entries if isinstance(e, GrupoExecutorMode)
    ]

    if grupo_executor_entries:
        if GRUPO_EXECUTOR_COLUMN not in fieldnames:
            warnings.append(
                f'sintetico.xlsx: INMS {inms_key}: {raw_csv_path} não tem '
                f"coluna '{GRUPO_EXECUTOR_COLUMN}' — aba não gerada"
            )
            return warnings
        if (
            inms_key == _INMS_1_1
            and base_config.target is not None
            and base_config.penalty is not None
            and inms_1_1_audit.has_required_columns(fieldnames)
        ):
            # Aba enriquecida (resumo executivo, memória de cálculo,
            # fora-do-prazo, auditoria de prazo) — só quando o CSV bruto
            # tem as colunas de detalhe (produção real, ambos os
            # órgãos); CSVs minimalistas (ex. fixtures de teste) caem no
            # renderer genérico abaixo, sem degradar silenciosamente.
            try:
                inms_1_1_audit.write_sheet(
                    workbook,
                    sheet_name,
                    categorias_file=categorias_file,
                    grupo_executor_entries=grupo_executor_entries,
                    whole_indicator_entries=whole_indicator_entries,
                    fieldnames=fieldnames,
                    rows=rows,
                    target_operator=base_config.target.operator,
                    target_value=base_config.target.value,
                    penalty_base_points=base_config.penalty.base_points,
                    penalty_step_points=base_config.penalty.step_points,
                    penalty_step_size_pct=base_config.penalty.step_size_pct,
                    contract=base_config.scope.contract,
                    periodo=periodo,
                    raw_csv_path=raw_csv_path,
                    generated_at=generated_at,
                )
            except ValueError as exc:
                # Falha de validação/qualidade de dado específica da aba
                # enriquecida não deve derrubar o restante do workbook —
                # degrada para o renderer genérico, como as demais
                # falhas por-INMS deste loop.
                warnings.append(
                    f'sintetico.xlsx: INMS {inms_key}: falha ao gerar aba '
                    f'enriquecida ({exc}) — usando renderer genérico'
                )
                _write_grupo_executor_sheet(
                    workbook,
                    sheet_name,
                    categorias_file,
                    grupo_executor_entries,
                    whole_indicator_entries,
                    fieldnames,
                    rows,
                    accepted_ids,
                )
        elif (
            inms_key == _INMS_1_2
            and base_config.target is not None
            and isinstance(base_config.calculation, SegmentedRatioCalculation)
            and inms_1_2_write.has_required_columns(fieldnames)
            and (
                category_params := _segmented_ratio_category_params(
                    base_config.calculation
                )
            )
            is not None
        ):
            # Aba enriquecida (resumo/memória/penalidade por categoria de
            # prioridade) — mesmas condições de degradação do INMS 1.1: só
            # quando o CSV bruto tem as colunas de detalhe e a config bate
            # com o vocabulário assumido pelo renderer (ver
            # `_segmented_ratio_category_params`).
            try:
                inms_1_2_write.write_sheet(
                    workbook,
                    sheet_name,
                    categorias_file=categorias_file,
                    grupo_executor_entries=grupo_executor_entries,
                    whole_indicator_entries=whole_indicator_entries,
                    fieldnames=fieldnames,
                    rows=rows,
                    target_operator=base_config.target.operator,
                    target_value=base_config.target.value,
                    categories=category_params,
                    step_size_pct=base_config.calculation.step_size_pct,
                    contract=base_config.scope.contract,
                    periodo=periodo,
                    raw_csv_path=raw_csv_path,
                    generated_at=generated_at,
                )
            except ValueError as exc:
                warnings.append(
                    f'sintetico.xlsx: INMS {inms_key}: falha ao gerar aba '
                    f'enriquecida ({exc}) — usando renderer genérico'
                )
                _write_grupo_executor_sheet(
                    workbook,
                    sheet_name,
                    categorias_file,
                    grupo_executor_entries,
                    whole_indicator_entries,
                    fieldnames,
                    rows,
                    accepted_ids,
                )
        elif (
            inms_key == _INMS_1_3
            and base_config.target is not None
            and base_config.penalty is not None
            and inms_1_3_write.has_required_columns(fieldnames)
        ):
            # Mesmo shape/condições de degradação do INMS 1.1 (ratio único,
            # `No prazo` S/N) — ver `excel/inms_1_3/write.py`.
            try:
                inms_1_3_write.write_sheet(
                    workbook,
                    sheet_name,
                    categorias_file=categorias_file,
                    grupo_executor_entries=grupo_executor_entries,
                    whole_indicator_entries=whole_indicator_entries,
                    fieldnames=fieldnames,
                    rows=rows,
                    target_operator=base_config.target.operator,
                    target_value=base_config.target.value,
                    penalty_base_points=base_config.penalty.base_points,
                    penalty_step_points=base_config.penalty.step_points,
                    penalty_step_size_pct=base_config.penalty.step_size_pct,
                    contract=base_config.scope.contract,
                    periodo=periodo,
                    raw_csv_path=raw_csv_path,
                    generated_at=generated_at,
                )
            except ValueError as exc:
                warnings.append(
                    f'sintetico.xlsx: INMS {inms_key}: falha ao gerar aba '
                    f'enriquecida ({exc}) — usando renderer genérico'
                )
                _write_grupo_executor_sheet(
                    workbook,
                    sheet_name,
                    categorias_file,
                    grupo_executor_entries,
                    whole_indicator_entries,
                    fieldnames,
                    rows,
                    accepted_ids,
                )
        elif _ratio_count_distinct_eligible(inms_key, base_config):
            # Aba enriquecida (identificação, resumo executivo, detalhe
            # por grupo executor com o critério real do
            # `numerator_filter`, memória de penalidade) — em vez do
            # genérico, que assume "No prazo"/`DataHoraFim` (colunas que
            # fontes como satisfação/telefonia não têm e por isso só
            # produziam traços).
            if not isinstance(base_config.calculation, RatioCalculation):
                raise ValueError('ratio exige `RatioCalculation`')
            if base_config.target is None:
                raise ValueError('ratio exige `target` no sintetico')
            if base_config.penalty is None:
                raise ValueError('ratio exige `penalty` no sintetico')
            _write_ratio_audit_sheet(
                workbook,
                sheet_name,
                categorias_file,
                grupo_executor_entries,
                whole_indicator_entries,
                base_config.calculation,
                base_config.target.operator,
                base_config.target.value,
                base_config.penalty.base_points,
                base_config.penalty.step_points,
                base_config.penalty.step_size_pct,
                base_config.indicator.name,
                rows,
                contract=base_config.scope.contract,
                periodo=periodo,
                raw_csv_path=raw_csv_path,
                generated_at=generated_at,
            )
        else:
            _write_grupo_executor_sheet(
                workbook,
                sheet_name,
                categorias_file,
                grupo_executor_entries,
                whole_indicator_entries,
                fieldnames,
                rows,
                accepted_ids,
            )
    elif isinstance(base_config.calculation, PrecomputedTableCalculation):
        if base_config.target is None:
            raise ValueError('precomputed exige `target` no sintetico')
        if (
            base_config.calculation.result_is_percent
            and base_config.calculation.name_column is not None
            and base_config.scope.contract
        ):
            # Aba enriquecida por-ativo (identificação, resumo executivo,
            # resultado a 4 casas decimais, memória de penalidade) — todo
            # `precomputed_table` percentual com `name_column` (1.4, 1.5,
            # 1.9, 1.13, 1.14 hoje) usa este renderer; indicadores em pontos
            # (`result_is_percent: false`, ex. 1.8) ficam no renderer
            # precomputed plano, que não assume escala percentual. Mesma
            # lógica de degradação que 1.1/1.2/1.3: se o CSV bruto não
            # trouxer `name_column` ou o contrato estiver vazio, cai no
            # renderer precomputed plano.
            _write_precomputed_audit_sheet(
                workbook,
                sheet_name,
                categorias_file,
                whole_indicator_entries,
                base_config.calculation,
                base_config.target.operator,
                base_config.target.value,
                rows,
                contract=base_config.scope.contract,
                periodo=periodo,
                raw_csv_path=raw_csv_path,
                generated_at=generated_at,
            )
        else:
            _write_precomputed_table_sheet(
                workbook,
                sheet_name,
                categorias_file,
                whole_indicator_entries,
                base_config.calculation,
                base_config.target.operator,
                base_config.target.value,
                rows,
            )
    elif (
        isinstance(base_config.calculation, RatioCalculation)
        and base_config.calculation.aggregation == 'sum'
        and base_config.calculation.sum_numerator_subtract_column is not None
        and base_config.calculation.denominator_filter is not None
    ):
        if base_config.target is None:
            raise ValueError('ratio_aggregate exige `target` no sintetico')
        if base_config.penalty is None:
            raise ValueError('ratio_aggregate exige `penalty` no sintetico')
        _write_ratio_aggregate_sheet(
            workbook,
            sheet_name,
            categorias_file,
            whole_indicator_entries,
            base_config.calculation,
            base_config.target.operator,
            base_config.target.value,
            base_config.penalty.base_points,
            base_config.penalty.step_points,
            base_config.penalty.step_size_pct,
            base_config.indicator.name,
            rows,
            contract=base_config.scope.contract,
            periodo=periodo,
            raw_csv_path=raw_csv_path,
            generated_at=generated_at,
        )
    elif _ratio_count_distinct_eligible(inms_key, base_config):
        if not isinstance(base_config.calculation, RatioCalculation):
            raise ValueError('ratio exige `RatioCalculation`')
        if base_config.target is None:
            raise ValueError('ratio exige `target` no sintetico')
        if base_config.penalty is None:
            raise ValueError('ratio exige `penalty` no sintetico')
        _write_ratio_audit_sheet(
            workbook,
            sheet_name,
            categorias_file,
            [],
            whole_indicator_entries,
            base_config.calculation,
            base_config.target.operator,
            base_config.target.value,
            base_config.penalty.base_points,
            base_config.penalty.step_points,
            base_config.penalty.step_size_pct,
            base_config.indicator.name,
            rows,
            contract=base_config.scope.contract,
            periodo=periodo,
            raw_csv_path=raw_csv_path,
            generated_at=generated_at,
        )
    else:
        _write_whole_indicator_sheet(
            workbook,
            sheet_name,
            categorias_file,
            whole_indicator_entries,
            fieldnames,
            rows,
            accepted_ids,
        )

    return warnings
