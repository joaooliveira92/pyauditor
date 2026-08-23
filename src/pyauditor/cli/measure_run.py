"""Loop de medição de `pyauditor measure` (ticket 07 SRP).

O corpo do `for` de `run_measure` (expansão de categorias em memória + caminho
single) e as closures `_handle_result`/`_hard_fail_todas_categorias` viram uma
classe `MeasureLoop` com estado próprio (outcomes/warnings/hard_failure) — sem
`nonlocal`. `run_measure` apenas orquestra: resolve entradas, roda o loop e
monta o `MeasureResult`.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from pyauditor.categoria_filter import (
    GRUPO_EXECUTOR_COLUMN,
    compute_categoria_values,
    outros_warning,
    unmatched_in_values_warnings,
)
from pyauditor.cli.measure_contracts import (
    IndicatorOutcome,
    _MeasuredIndicator,
    _sanitize_indicator_id,
)
from pyauditor.cli.measure_inputs import (
    _inms_key_from_contractual_id,
)
from pyauditor.cli.results import WRITE_FAILURE_HINT
from pyauditor.config.categorias import GrupoExecutorMode
from pyauditor.config.manifest import DatasetManifest
from pyauditor.config.models import IndicatorConfig
from pyauditor.engine.pipeline import (
    MeasurementProvenance,
    MeasurementResult,
    measure,
    measurement_source,
)
from pyauditor.engine.quality_gates import QualityGateRunner
from pyauditor.engine.strategies import SHAPE_REGISTRY
from pyauditor.engine.version import pipeline_version
from pyauditor.logging import log_event, logger
from pyauditor.periodo import PeriodoAfericao
from pyauditor.rom.render import render_rom
from pyauditor.rom.summary import summarize

__all__: tuple[str, ...] = ('MeasureLoop', 'MeasureLoopResult')


@dataclass(frozen=True)
class MeasureLoopResult:
    """Estado final do loop (sem closures/`nonlocal`)."""

    outcomes: list[IndicatorOutcome] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    any_hard_failure: bool = False
    collected: list[_MeasuredIndicator] = field(default_factory=list)


class MeasureLoop:
    """Mede todos os indicadores de uma execução de `measure`.

    Acumula outcomes/warnings/hard_failure em atributos de instância (em vez
    de closures com `nonlocal`).
    """

    def __init__(
        self,
        *,
        orgao: str,
        competencia: str,
        competencia_data_dir: Path,
        target_dir: Path,
        per_inms: dict[str, list[tuple[str, GrupoExecutorMode]]],
        derived_config_stems: set[str],
        categorias_file: object | None,
        manifest: DatasetManifest | None,
        periodo: PeriodoAfericao | None,
        strict: bool,
        suppress_duplicate_split_warnings: bool,
        capa_fields: dict[str, object],
    ) -> None:
        self.orgao = orgao
        self.competencia = competencia
        self.competencia_data_dir = competencia_data_dir
        self.target_dir = target_dir
        self.per_inms = per_inms
        self.derived_config_stems = derived_config_stems
        self.categorias_file = categorias_file
        self.manifest = manifest
        self.periodo = periodo
        self.strict = strict
        # Resolvido uma vez aqui — os pontos de uso abaixo consultam este
        # atributo, não o parâmetro bruto, para não repetir a negação.
        self._suppress_period_logs = suppress_duplicate_split_warnings
        self.capa_fields = capa_fields
        self.outcomes: list[IndicatorOutcome] = []
        self.warnings: list[str] = []
        self.hard_failure = False

    def run_configs(
        self,
        configs: list[tuple[Path, str, IndicatorConfig]],
        collect: list[_MeasuredIndicator] | None = None,
    ) -> MeasureLoopResult:
        for config_path, config_hash, config in configs:
            if config_path.stem in self.derived_config_stems:
                continue
            self._measure_config(
                config_path,
                config_hash,
                config,
                collect=collect,
            )
        return MeasureLoopResult(
            outcomes=self.outcomes,
            warnings=self.warnings,
            any_hard_failure=self.hard_failure,
            collected=collect or [],
        )

    def _measure_config(
        self,
        config_path: Path,
        config_hash: str,
        config: IndicatorConfig,
        *,
        collect: list[_MeasuredIndicator] | None,
    ) -> None:
        contractual_id = config.indicator.contractual_id
        inms_key = _inms_key_from_contractual_id(contractual_id)
        entries = self.per_inms.get(inms_key) if inms_key is not None else None

        if (
            entries is not None
            and self.categorias_file is not None
            and inms_key is not None
        ):
            self._measure_categorias(
                config_path,
                config,
                inms_key,
                entries,
                collect=collect,
            )
            return

        self._measure_single(
            config_path,
            config_hash,
            config,
            collect=collect,
        )

    def _measure_categorias(
        self,
        config_path: Path,
        config: IndicatorConfig,
        inms_key: str,
        entries: list[tuple[str, GrupoExecutorMode]],
        *,
        collect: list[_MeasuredIndicator] | None,
    ) -> None:
        """Backbone (ticket 05): resolve->valida->lê->filtra o bruto uma vez
        para todas as categorias. `_suppress_period_logs` evita duplicar
        WARN/INFO de período quando `split` já rodou na mesma passada."""
        competencia = self.competencia
        target_dir = self.target_dir
        contractual_id = config.indicator.contractual_id
        try:
            bundle = measurement_source(
                config,
                self.competencia_data_dir,
                self.manifest,
                config_path=config_path,
                periodo=self.periodo,
                strict=self.strict,
                emit_period_filter_logs=not self._suppress_period_logs,
            )
        except FileNotFoundError:
            for cat_key, _ in entries:
                derived_id = f'{config.indicator.id}.{cat_key}'
                safe_id = _sanitize_indicator_id(derived_id)
                rom_path = target_dir / f'{safe_id}.md'
                summary_path = target_dir / f'{safe_id}.json'
                warning = ''.join(
                    [
                        f'{contractual_id} ({config.scope.orgao}/',
                        f'{competencia}, {cat_key}): não ativado — ',
                        'dataset ausente',
                    ]
                )
                logger.warning(warning)
                self.warnings.append(warning)
                self.outcomes.append(
                    IndicatorOutcome(
                        contractual_id=contractual_id,
                        rom_path=rom_path,
                        summary_path=summary_path,
                        hard_failure=False,
                        error=None,
                        not_activated=True,
                    )
                )
            return
        except (OSError, ValueError) as exc:
            self._hard_fail_todas_categorias(
                f'{contractual_id}: exceção na medição: {exc}',
                entries=entries,
                indicator_id=config.indicator.id,
                contractual_id=contractual_id,
            )
            return

        raw_csv_path = bundle.csv_path
        fieldnames = bundle.fieldnames
        rows = bundle.rows
        delimiter = bundle.delimiter
        encoding = bundle.encoding
        dropped_out_of_period = bundle.dropped_out_of_period
        undated_dropped = bundle.undated_dropped

        if GRUPO_EXECUTOR_COLUMN not in fieldnames:
            message = ''.join(
                [
                    f'{contractual_id}: exceção na medição: ',
                    f'{raw_csv_path} não tem coluna ',
                    f"'{GRUPO_EXECUTOR_COLUMN}' — declarado mode: ",
                    'grupo_executor em categorias.yaml',
                ]
            )
            self._hard_fail_todas_categorias(
                message,
                entries=entries,
                indicator_id=config.indicator.id,
                contractual_id=contractual_id,
            )
            return

        real_values = {row[GRUPO_EXECUTOR_COLUMN] for row in rows}
        if not self._suppress_period_logs:
            for w in unmatched_in_values_warnings(
                inms_key=inms_key,
                orgao=config.scope.orgao,
                competencia=competencia,
                entries=entries,
                real_values=real_values,
                raw_csv_path=raw_csv_path,
            ):
                logger.warning(w)
                self.warnings.append(w)
        per_categoria_values, outros_values = compute_categoria_values(
            entries, real_values
        )
        for cat_key, effective_values in per_categoria_values.items():
            filtered_rows = [
                row
                for row in rows
                if row[GRUPO_EXECUTOR_COLUMN] in effective_values
            ]
            derived_indicator = config.indicator.model_copy(
                update={'id': f'{config.indicator.id}.{cat_key}'}
            )
            derived_config = config.model_copy(
                update={
                    'indicator': derived_indicator,
                    'acceptance_test': None,
                }
            )
            derived_safe_id = _sanitize_indicator_id(
                derived_config.indicator.id
            )
            rom_path = target_dir / f'{derived_safe_id}.md'
            summary_path = target_dir / f'{derived_safe_id}.json'
            try:
                gate_runner = QualityGateRunner(
                    derived_config.quality_gates.checks,
                    id_column=derived_config.source.id_column,
                )
                gate_report = gate_runner.run(filtered_rows)
                strategy = SHAPE_REGISTRY[derived_config.calculation.shape]
                calculation = strategy.calculate(
                    derived_config, gate_report.accepted
                )
                csv_hash = hashlib.sha256(raw_csv_path.read_bytes()).hexdigest()
                derived_hash = hashlib.sha256(
                    json.dumps(
                        derived_config.model_dump(mode='json'),
                        sort_keys=True,
                    ).encode()
                ).hexdigest()
                provenance = MeasurementProvenance(
                    config_path=config_path,
                    config_hash=derived_hash,
                    csv_path=raw_csv_path,
                    csv_hash=csv_hash,
                    delimiter=delimiter,
                    encoding=encoding,
                    processed_at=datetime.now(),
                    pipeline_version=pipeline_version(),
                )
                result = MeasurementResult(
                    config=derived_config,
                    quality_gate_report=gate_report,
                    calculation=calculation,
                    provenance=provenance,
                    dropped_out_of_period=dropped_out_of_period,
                    undated_dropped=undated_dropped,
                )
            except Exception as exc:
                message = ''.join(
                    [
                        f'{contractual_id}.{cat_key}: exceção na ',
                        f'medição: {exc}',
                    ]
                )
                logger.error(message)
                self.hard_failure = True
                self.outcomes.append(
                    IndicatorOutcome(
                        contractual_id=contractual_id,
                        rom_path=rom_path,
                        summary_path=summary_path,
                        hard_failure=True,
                        error=message,
                    )
                )
                continue
            self._handle_result(
                result,
                derived_safe_id,
                rom_path,
                summary_path,
                contractual_id,
                derived_config.indicator.id,
                derived_config.scope.orgao,
                collect=collect,
            )
        outros_rows = [
            row for row in rows if row[GRUPO_EXECUTOR_COLUMN] in outros_values
        ]
        if outros_rows and not self._suppress_period_logs:
            w = outros_warning(
                inms_key=inms_key,
                orgao=config.scope.orgao,
                competencia=competencia,
                outros_count=len(outros_rows),
            )
            logger.warning(w)
            self.warnings.append(w)

    def _measure_single(
        self,
        config_path: Path,
        config_hash: str,
        config: IndicatorConfig,
        *,
        collect: list[_MeasuredIndicator] | None,
    ) -> None:
        contractual_id = config.indicator.contractual_id
        safe_id = _sanitize_indicator_id(config.indicator.id)
        rom_path = self.target_dir / f'{safe_id}.md'
        summary_path = self.target_dir / f'{safe_id}.json'
        try:
            result = self.measure_single_call(
                config,
                config_path,
                config_hash,
            )
        except FileNotFoundError:
            scope_orgao = getattr(
                getattr(config, 'scope', None), 'orgao', self.orgao
            )
            warning = ''.join(
                [
                    f'{contractual_id} ({scope_orgao}/{self.competencia}): ',
                    'não ativado — dataset ausente ',
                    '(serviço não requisitado no período)',
                ]
            )
            logger.warning(warning)
            self.warnings.append(warning)
            self.outcomes.append(
                IndicatorOutcome(
                    contractual_id=contractual_id,
                    rom_path=rom_path,
                    summary_path=summary_path,
                    hard_failure=False,
                    error=None,
                    not_activated=True,
                )
            )
            return
        except Exception as exc:
            message = f'{contractual_id}: exceção na medição: {exc}'
            logger.error(message)
            self.hard_failure = True
            self.outcomes.append(
                IndicatorOutcome(
                    contractual_id=contractual_id,
                    rom_path=rom_path,
                    summary_path=summary_path,
                    hard_failure=True,
                    error=message,
                )
            )
            return
        self._handle_result(
            result,
            safe_id,
            rom_path,
            summary_path,
            contractual_id,
            config.indicator.id,
            getattr(getattr(config, 'scope', None), 'orgao', self.orgao),
            collect=collect,
        )

    def measure_single_call(
        self,
        config: IndicatorConfig,
        config_path: Path,
        config_hash: str,
    ) -> MeasurementResult:
        """`measure` sobre uma config (whole_indicator). Override em teste."""
        return measure(
            config,
            data_dir=self.competencia_data_dir,
            manifest=self.manifest,
            config_path=config_path,
            config_hash=config_hash,
            periodo=self.periodo,
            strict=self.strict,
            emit_period_filter_logs=not self._suppress_period_logs,
        )

    def _hard_fail_todas_categorias(
        self,
        message: str,
        *,
        entries: list[tuple[str, GrupoExecutorMode]],
        indicator_id: str,
        contractual_id: str,
    ) -> None:
        """Marca todas as categorias derivadas como hard-failure com a mesma
        mensagem — falha técnica do dataset bruto, não de uma categoria."""
        logger.error(message)
        self.hard_failure = True
        for cat_key, _ in entries:
            derived_id = f'{indicator_id}.{cat_key}'
            safe_id = _sanitize_indicator_id(derived_id)
            rom_path = self.target_dir / f'{safe_id}.md'
            summary_path = self.target_dir / f'{safe_id}.json'
            self.outcomes.append(
                IndicatorOutcome(
                    contractual_id=contractual_id,
                    rom_path=rom_path,
                    summary_path=summary_path,
                    hard_failure=True,
                    error=message,
                )
            )

    def _handle_result(
        self,
        result: MeasurementResult,
        safe_id: str,
        rom_path: Path,
        summary_path: Path,
        contractual_id: str,
        indicator_id: str,
        scope_orgao: str,
        *,
        collect: list[_MeasuredIndicator] | None,
    ) -> None:
        try:
            _ = rom_path.write_text(
                render_rom(
                    result,
                    capa_fields=self.capa_fields,
                    competencia=self.competencia,
                    periodo=self.periodo,
                ),
                encoding='utf-8',
            )
            summary = summarize(result)
            _ = summary_path.write_text(
                json.dumps(summary.to_dict(), ensure_ascii=False, indent=2),
                encoding='utf-8',
            )
        except OSError as exc:
            message = ''.join(
                [
                    f'falha ao escrever {rom_path}: {exc} — ',
                    WRITE_FAILURE_HINT,
                ]
            )
            logger.error(message)
            self.hard_failure = True
            self.outcomes.append(
                IndicatorOutcome(
                    contractual_id=contractual_id,
                    rom_path=rom_path,
                    summary_path=summary_path,
                    hard_failure=True,
                    error=message,
                )
            )
            return
        if result.hard_failure:
            self.hard_failure = True
            error = ''.join(
                [
                    f'{contractual_id}: falha de medição — ',
                    'nenhuma linha sobreviveu aos quality gates ',
                    f'({rom_path})',
                ]
            )
            logger.error(error)
            self.outcomes.append(
                IndicatorOutcome(
                    contractual_id=contractual_id,
                    rom_path=rom_path,
                    summary_path=summary_path,
                    hard_failure=True,
                    error=error,
                )
            )
        elif getattr(result, 'systematic_failure', False):
            self.hard_failure = True
            systematic_error = ''.join(
                [
                    f'{contractual_id}: não-conformidade sistemática — ',
                    f'resultado {summary.result_pct:.2f}% sempre ',
                    f'não-conforme, possível bug de cálculo ({rom_path})',
                ]
            )
            logger.error(systematic_error)
            self.outcomes.append(
                IndicatorOutcome(
                    contractual_id=contractual_id,
                    rom_path=rom_path,
                    summary_path=summary_path,
                    hard_failure=True,
                    error=systematic_error,
                )
            )
        else:
            status_label = (
                'conforme'
                if getattr(summary, 'conforms', True)
                else 'nao_conforme'
            )
            if getattr(summary, 'systematic_failure', False):
                status_label = 'nao_conforme_sistematica'
            log_event(
                'indicator_measured',
                'indicador apurado',
                'DEBUG',
                orgao=self.orgao or '',
                codigo=contractual_id,
                rom_path=str(rom_path),
                status=status_label,
            )
            self.outcomes.append(
                IndicatorOutcome(
                    contractual_id=contractual_id,
                    rom_path=rom_path,
                    summary_path=summary_path,
                    hard_failure=False,
                    error=None,
                )
            )
        if collect is not None:
            collect.append(
                _MeasuredIndicator(
                    indicator_id=indicator_id,
                    safe_id=safe_id,
                    orgao=scope_orgao,
                    result=result,
                    capa_fields=self.capa_fields,
                )
            )
