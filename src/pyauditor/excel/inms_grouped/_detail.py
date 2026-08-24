"""Recomputação do detalhamento por Grupo executor / por ativo, direto de
`config_dir`/`data_dir` — a única responsabilidade deste módulo é reproduzir,
por subconjunto (grupo executor ou ativo), a mesma aritmética que o motor
oficial (`measure`) já publica agregada no `INMS_BASE`. Ver o docstring do
pacote (`inms_grouped/__init__.py`) para a justificativa completa de por que
isso não é fabricação de números.
"""

from __future__ import annotations

from math import isnan
from pathlib import Path
from typing import cast

from pyauditor.categoria_filter import (
    GRUPO_EXECUTOR_COLUMN,
    base_config_stem,
    compute_categoria_values,
)
from pyauditor.cli.measure_inputs import resolve_measure_inputs
from pyauditor.config.categorias import CategoriasFile, GrupoExecutorMode
from pyauditor.config.models import IndicatorConfig, PrecomputedTableCalculation
from pyauditor.config.niveis import NIVEL_BY_CATEGORIA
from pyauditor.config.resolution import per_orgao_paths
from pyauditor.engine.pipeline import measurement_source
from pyauditor.engine.quality_gates import QualityGateRunner
from pyauditor.engine.strategies import SHAPE_REGISTRY
from pyauditor.engine.strategies._numbers import parse_decimal
from pyauditor.periodo import month_bounds

from ._types import (
    _AUDIT_REVIEW_LABEL,
    _CONSOLIDATABLE_SHAPES,
    _ORGAOS,
    _PRECOMPUTED_BREAKDOWN_CODES,
    _SEM_NIVEL,
    GrupoRow,
    _CodeInfo,
)


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
        cast(dict[str, object], result.memoria)
    )
    return numerator or 0.0, denominator or 0.0


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

    `consolidatable=True` sempre: por pedido explícito, "Consolidado" (o
    pai comum de "Consolidado - MinC"/"Consolidado - MTur") soma os
    numerador/denominador dos dois órgãos — a mesma soma que já gera cada
    subtotal por órgão, só estendida ao outro nível. Diferente do resto do
    pipeline (`excel/orgao_consolidation.py`'s `PER_ASSET_CONTRACTUAL_IDS`),
    que não expõe esse total entre órgãos em nenhum outro lugar por não ter
    validado a fórmula contra uma fonte primária — aqui é só aritmética
    direta sobre números já corretos, não uma fórmula contratual nova.
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
                    consolidatable=True,
                )

    return rows_by_inms, info_by_inms
