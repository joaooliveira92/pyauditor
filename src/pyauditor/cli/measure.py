"""`pyauditor measure <competência>` — run every configured indicator, write one
ROM Markdown per indicator, report hard failures (spec §4/§6).

Alongside each `<indicator.id>.md` ROM, also writes a `<indicator.id>.json`
structured summary (see `rom/summary.py`) — `report` (ticket 09) reads these
JSON sidecars rather than re-parsing the ROM's prose Markdown.

Datasets are organized per competência: `measure 2026-06 --data-dir input`
reads every CSV from `input/2026/06/` (derived from the competência, never
from the data-dir root). Keeping each competência in its own folder lets one
project hold the data of every past aferição side by side.

Spec competencia-cli-equipe: os ROMs recebem Competência/Período do argumento
da CLI (`periodo`) e os Responsáveis de `equipe.csv` (`equipe_path`) — nada
vem mais da capa. Com `periodo`, tanto o caminho single (whole_indicator) via
`engine.measure()` quanto o caminho derivado (categorias em memória) filtram
pela janela da competência através do backbone `measurement_source()`
(ticket 05) — `suppress_duplicate_split_warnings` evita emitir o mesmo
aviso duas vezes quando `run` já rodou `split` na mesma passada.

Resolução de entradas (`resolve_measure_inputs`/`MeasureInputs`), o loop de
medição (`MeasureLoop`) e os contratos locais (`_MeasuredIndicator`, o
sanitizador de nome de arquivo) vivem neste único módulo: "medir um INMS
segmentado por Categoria" é um conceito, não uma pilha de camadas técnicas
— `MeasureLoop` recebe `MeasureInputs` já resolvido em vez de repetir os
mesmos campos num segundo formato de construtor. Os ROMs combinados `both`
ficam em `cli/measure_combined.py` (concern distinto: junta dois órgãos, não
mede um indicador).
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Final

from pyauditor.categoria_filter import (
    GRUPO_EXECUTOR_COLUMN,
    base_config_stem,
    compute_categoria_values,
    outros_warning,
    unmatched_in_values_warnings,
)
from pyauditor.cli.measure_combined import write_combined_roms
from pyauditor.cli.results import (
    DIR_FAILURE_HINT,
    WRITE_FAILURE_HINT,
    DependencyCheck,
    validate_competencia,
)
from pyauditor.cli.split_derive import derive_config
from pyauditor.commands import contracts
from pyauditor.commands.contracts import IndicatorOutcome
from pyauditor.config.categorias import GrupoExecutorMode, load_categorias
from pyauditor.config.manifest import DatasetManifest
from pyauditor.config.models import IndicatorConfig
from pyauditor.engine.pipeline import (
    MeasurementProvenance,
    MeasurementResult,
    discover_config_files,
    measure,
    measurement_source,
)
from pyauditor.engine.quality_gates import QualityGateRunner
from pyauditor.engine.strategies import SHAPE_REGISTRY
from pyauditor.engine.version import pipeline_version
from pyauditor.excel.equipe import RESPONSAVEL_LABELS, read_responsaveis
from pyauditor.logging import log_event, logger
from pyauditor.periodo import PeriodoAfericao
from pyauditor.rom.render import render_rom
from pyauditor.rom.summary import summarize

__all__: Final[tuple[str, ...]] = (
    'IndicatorOutcome',
    'MeasureResult',
    '_MeasuredIndicator',
    'check_measure_ready',
    'run_measure',
    'write_combined_roms',
)

# `MeasureResult` vive no contrato neutro `pyauditor.commands.contracts`
# (ticket 11 SRP) — reexportado aqui para preservar a API pública.
MeasureResult = contracts.MeasureResult

_UNSAFE_ID_CHARS_RE: Final = re.compile(r'[^A-Za-z0-9._-]')


def _sanitize_indicator_id(raw: str) -> str:
    """Cria um nome de arquivo seguro sem escapar do diretório de saída."""
    sanitized = _UNSAFE_ID_CHARS_RE.sub('_', raw).strip('._')
    return sanitized or '_indicator'


@dataclass(frozen=True, slots=True)
class _MeasuredIndicator:
    """Indicador medido + cells de Responsáveis do seu órgão."""

    indicator_id: str
    safe_id: str
    orgao: str
    result: MeasurementResult
    capa_fields: dict[str, object]


def _inms_key_from_contractual_id(contractual_id: str) -> str | None:
    """`INMS 1.1` -> `1.1` — chave usada em `categorias.yaml`."""
    parts = contractual_id.strip().split()
    if not parts:
        return None
    last = parts[-1]
    # Valida formato 1.N
    if '.' not in last:
        return None
    return last


@dataclass(frozen=True)
class MeasureInputs:
    """Entradas validadas e resolvidas de uma execução de `measure`."""

    orgao: str
    competencia_data_dir: Path
    configs: list[tuple[Path, str, IndicatorConfig]]
    target_dir: Path
    capa_fields: dict[str, object]
    warnings: list[str] = field(default_factory=list)
    per_inms: dict[str, list[tuple[str, GrupoExecutorMode]]] = field(
        default_factory=dict
    )
    derived_config_stems: set[str] = field(default_factory=set)
    categorias_file: object | None = None


def _load_responsaveis(
    equipe_path: Path | None,
    warnings: list[str],
) -> dict[str, object]:
    """Responsáveis do ROM vêm exclusivamente de `equipe.csv` (spec §6) —
    ausente/malformado é warning + '[a preencher]', nunca falha técnica."""
    capa_fields: dict[str, object] = {}
    if equipe_path is None:
        return capa_fields

    campos_equipe, avisos_equipe = read_responsaveis(equipe_path)
    capa_fields.update(campos_equipe)
    for warning in avisos_equipe:
        logger.warning(warning)
        warnings.append(warning)
    empty_fields = [f for f in RESPONSAVEL_LABELS if not capa_fields.get(f)]
    if empty_fields:
        warning = ''.join(
            [
                f'{equipe_path}: sem preencher: ',
                f'{", ".join(empty_fields)} — ROM mostra ',
                "'[a preencher]' nesses campos",
            ]
        )
        logger.warning(warning)
        warnings.append(warning)
    return capa_fields


def _load_categorias(
    config_dir: Path,
    expected_orgao: str | None,
    warnings: list[str],
) -> tuple[object | None, dict[str, list[tuple[str, GrupoExecutorMode]]]]:
    """Single-source categorias: carrega uma vez por execução (fallback para
    parent/<orgao>/categorias.yaml quando config_dir é _shared)."""
    categorias_file = None
    per_inms: dict[str, list[tuple[str, GrupoExecutorMode]]] = {}
    if expected_orgao is None:
        return categorias_file, per_inms

    categorias_path = config_dir / 'categorias.yaml'
    if not categorias_path.exists() and config_dir.name == '_shared':
        fallback = config_dir.parent / expected_orgao / 'categorias.yaml'
        if fallback.exists():
            categorias_path = fallback
    if not categorias_path.exists():
        return categorias_file, per_inms

    try:
        categorias_file = load_categorias(categorias_path)
        for cat_key, cat in categorias_file.categorias.items():
            for cat_inms_key, entry in cat.inms.items():
                if isinstance(entry, GrupoExecutorMode):
                    per_inms.setdefault(cat_inms_key, []).append(
                        (cat_key, entry)
                    )
        logger.debug('categorias carregadas de %s', categorias_path)
    except (OSError, ValueError) as exc:
        logger.warning(
            'falha ao carregar categorias %s: %s',
            categorias_path,
            exc,
        )
    return categorias_file, per_inms


def _derived_config_stems(
    per_inms: dict[str, list[tuple[str, GrupoExecutorMode]]],
) -> set[str]:
    """ADR 0002 (compat retroativa): configs por categoria que o `split`
    materializa em disco são descartadas silenciosamente da descoberta — o
    caminho de fato usado hoje é a expansão em memória."""
    derived_config_stems: set[str] = set()
    for categoria_inms_key, categoria_entries in per_inms.items():
        try:
            stem = base_config_stem(categoria_inms_key)
        except ValueError:
            continue
        derived_config_stems.update(
            f'{stem}.{cat_key}' for cat_key, _entry in categoria_entries
        )
    return derived_config_stems


def resolve_measure_inputs(
    competencia: str,
    config_dir: Path,
    data_dir: Path,
    output_dir: Path,
    *,
    expected_orgao: str | None = None,
    equipe_path: Path | None = None,
    manifest: DatasetManifest | None = None,
) -> tuple[MeasureInputs | None, str | None]:
    """Valida e resolve todas as entradas de `measure`.

    Returns:
        ``(inputs, None)`` em sucesso ou ``(None, mensagem_de_erro)`` quando
        uma etapa de entrada falha (competência inválida, configs ausentes,
        diretório de saída sem permissão). Warnings de equipe/categorias vão
        para dentro de ``inputs.warnings``.
    """
    orgao = expected_orgao or ''

    competencia_error = validate_competencia(competencia)
    if competencia_error is not None:
        return None, competencia_error

    year, month = competencia.split('-')
    competencia_data_dir = data_dir / year / month

    try:
        configs = discover_config_files(
            config_dir, expected_orgao=expected_orgao
        )
    except (OSError, ValueError) as exc:
        return None, f'falha ao carregar configs de {config_dir}: {exc}'
    if not configs:
        return None, f'nenhum config encontrado em {config_dir}'

    target_dir = output_dir / competencia
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        message = f'falha ao criar diretório {target_dir}: {exc}'
        return None, f'{message} — {DIR_FAILURE_HINT}'

    warnings: list[str] = []
    capa_fields = _load_responsaveis(equipe_path, warnings)
    categorias_file, per_inms = _load_categorias(
        config_dir, expected_orgao, warnings
    )
    derived_config_stems = _derived_config_stems(per_inms)

    inputs = MeasureInputs(
        orgao=orgao,
        competencia_data_dir=competencia_data_dir,
        configs=configs,
        target_dir=target_dir,
        capa_fields=capa_fields,
        warnings=warnings,
        per_inms=per_inms,
        derived_config_stems=derived_config_stems,
        categorias_file=categorias_file,
    )
    return inputs, None


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
        inputs: MeasureInputs,
        competencia: str,
        manifest: DatasetManifest | None,
        periodo: PeriodoAfericao | None,
        strict: bool,
        suppress_duplicate_split_warnings: bool,
    ) -> None:
        # `inputs` já resolveu orgao/dirs/per_inms/categorias/capa_fields —
        # não repetir esse formato num segundo construtor: os atributos
        # abaixo só desempacotam `inputs`, não o modelam de novo.
        self.orgao = inputs.orgao
        self.competencia = competencia
        self.competencia_data_dir = inputs.competencia_data_dir
        self.target_dir = inputs.target_dir
        self.per_inms = inputs.per_inms
        self.derived_config_stems = inputs.derived_config_stems
        self.categorias_file = inputs.categorias_file
        self.manifest = manifest
        self.periodo = periodo
        self.strict = strict
        # Resolvido uma vez aqui — os pontos de uso abaixo consultam este
        # atributo, não o parâmetro bruto, para não repetir a negação.
        self._suppress_period_logs = suppress_duplicate_split_warnings
        self.capa_fields = inputs.capa_fields
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
            derived_config = derive_config(config, cat_key)
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


def check_measure_ready(*_args: object, **_kwargs: object) -> DependencyCheck:
    """`measure` only needs configs+data, both external inputs it validates
    itself — no dependency on another Command's output."""
    return DependencyCheck(satisfied=True, missing=())


def run_measure(
    competencia: str,
    config_dir: Path,
    data_dir: Path,
    output_dir: Path,
    manifest: DatasetManifest | None = None,
    *,
    expected_orgao: str | None = None,
    equipe_path: Path | None = None,
    periodo: PeriodoAfericao | None = None,
    strict: bool = False,
    collect: list[_MeasuredIndicator] | None = None,
    suppress_duplicate_split_warnings: bool = False,
) -> MeasureResult:
    """*suppress_duplicate_split_warnings* (ticket 05): `True` quando `split`
    já rodou para esta competência/órgão na mesma passada de `run` (o
    orchestration sempre despacha `split` antes de `measure`) — o caminho
    categorial em memória então suprime o próprio WARN de janela vazia e o
    INFO de descarte, já que `split` os logou para o mesmo dataset bruto.
    `pyauditor measure` isolado (default `False`) recebe o WARN/INFO aqui —
    antes este caminho nunca os emitia, ao contrário do caminho single
    (whole_indicator) abaixo."""
    orgao = expected_orgao or ''

    def _error(message: str) -> MeasureResult:
        logger.error(message)
        return MeasureResult(
            status='error',
            competencia=competencia,
            orgao=orgao,
            indicators=(),
            warnings=(),
            error_message=message,
        )

    inputs, error = resolve_measure_inputs(
        competencia,
        config_dir,
        data_dir,
        output_dir,
        expected_orgao=expected_orgao,
        equipe_path=equipe_path,
        manifest=manifest,
    )
    if error is not None:
        return _error(error)
    if inputs is None:
        return _error('falha interna: entradas não resolvidas')

    loop = MeasureLoop(
        inputs=inputs,
        competencia=competencia,
        manifest=manifest,
        periodo=periodo,
        strict=strict,
        suppress_duplicate_split_warnings=suppress_duplicate_split_warnings,
    )
    result = loop.run_configs(inputs.configs, collect=collect)

    warnings = inputs.warnings + result.warnings
    any_hard_failure = result.any_hard_failure
    outcomes = result.outcomes

    # Resumo conciso por órgão (INFO) — no lugar das N linhas repetidas.
    total = len(outcomes)
    ok = sum(1 for o in outcomes if not o.hard_failure)
    log_event(
        'measure_done',
        f'{orgao or "órgão"}: {ok}/{total} indicador(es) apurado(s)',
        'INFO',
        orgao=orgao,
        competencia=competencia,
        status='error' if any_hard_failure else 'done',
    )

    error_message = (
        'um ou mais indicadores tiveram falha de medição'
        if any_hard_failure
        else None
    )
    return MeasureResult(
        status='error' if any_hard_failure else 'done',
        competencia=competencia,
        orgao=orgao,
        indicators=tuple(outcomes),
        warnings=tuple(warnings),
        error_message=error_message,
    )
