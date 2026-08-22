"""Orchestrates one indicator's measurement: parse config -> load CSV -> quality
gates -> calculation strategy -> ROM-ready result.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from math import isclose
from pathlib import Path

from pyauditor.categoria_filter import read_raw_csv
from pyauditor.config.manifest import DatasetManifest
from pyauditor.config.models import Filter, IndicatorConfig
from pyauditor.engine.discovery import (
    discover_config_files,
    discover_configs,
    load_config,
)
from pyauditor.engine.loading import load_rows, resolve_source
from pyauditor.engine.quality_gates import QualityGateReport, QualityGateRunner
from pyauditor.engine.strategies import SHAPE_REGISTRY
from pyauditor.engine.strategies.base import CalculationResult
from pyauditor.engine.version import pipeline_version
from pyauditor.logging import logger
from pyauditor.periodo import (
    PeriodoAfericao,
    discard_message,
    empty_window_message,
    filter_periodo,
    require_period_column,
)

__all__ = (
    'MeasurementProvenance',
    'MeasurementResult',
    'SourceBundle',
    'discover_config_files',
    'discover_configs',
    'load_config',
    'load_rows',
    'measure',
    'measurement_source',
    'pipeline_version',
    'resolve_source',
)


@dataclass(frozen=True)
class MeasurementProvenance:
    """Where the numbers came from — the ROM's "Identificação" section reads
    this directly instead of the caller re-deriving it (spec:
    .scratch/melhoria_rom/map.md)."""

    config_path: Path | None
    config_hash: str | None
    csv_path: Path
    csv_hash: str
    delimiter: str
    encoding: str
    processed_at: datetime
    pipeline_version: str


@dataclass(frozen=True)
class SourceBundle:
    """Resultado do backbone `measurement_source()`: fonte resolvida, lida,
    filtrada por período e avaliada pelos quality gates — tudo que os 4
    reimplementadores do pipeline de medição (`engine.measure`,
    `excel.sintetico`, `cli.split`, `cli.measure`) precisavam recalcular
    cada um a seu jeito antes deste backbone existir (ticket 02)."""

    config: IndicatorConfig
    csv_path: Path
    delimiter: str
    encoding: str
    fieldnames: list[str]
    rows: list[dict[str, str]]
    gate_report: QualityGateReport
    accepted_ids: set[int]
    dropped_out_of_period: int | None
    undated_dropped: int | None


@dataclass(frozen=True)
class MeasurementResult:
    config: IndicatorConfig
    quality_gate_report: QualityGateReport
    calculation: CalculationResult
    provenance: MeasurementProvenance
    # Filtro de período (§5): None quando o filtro não rodou (chamador sem
    # periodo — só teste unitário). Sidecar novo carrega os valores.
    dropped_out_of_period: int | None = None
    undated_dropped: int | None = None

    @property
    def hard_failure(self) -> bool:
        """Quality gates rejected every row that existed — not the same as a
        source
        CSV that had zero rows to begin with (a legitimately empty competência,
        e.g. INMS 1.3/1.8/1.9/1.10 before manual data entry exists)."""
        report = self.quality_gate_report
        return len(report.accepted) == 0 and len(report.rejected) > 0

    @property
    def systematic_failure(self) -> bool:
        """Não-conformidade sistemática/estrutural: o cálculo rodou sem erro
        mas está sempre não-conforme com resultado extremo (0%). Distinto de
        não-conformidade pontual/esperada, que continua não sendo
        hard_failure."""
        if self.hard_failure:
            return False
        if self.calculation.conforms:
            return False
        if len(self.quality_gate_report.accepted) == 0:
            return False
        # Heurística mínima de sistemático: resultado 0% com linhas aceitas
        # (bug de cálculo que zera o resultado) — não marca pontual onde
        # result_pct é, ex., 85% abaixo da meta de 98%
        # Para shapes não-percentuais (ex. INMS 1.8 precomputed_table com
        # result_is_percent=false) o headline é sempre 0.0 por design — não
        # é bug, então não deve ser marcado como sistemático.
        from pyauditor.config.models import PrecomputedTableCalculation

        calc = self.config.calculation
        if (
            isinstance(calc, PrecomputedTableCalculation)
            and not calc.result_is_percent
        ):
            return False
        return isclose(self.calculation.result_pct, 0.0)


def _collect_config_columns(config: IndicatorConfig) -> set[str]:
    """All column names referenced in *config* that must exist in the CSV
    header.
    ``source.id_column`` é metadata para rastreabilidade, não participa do
    cálculo — não é validada aqui (muitos CSVs sintéticos/testes não a têm)."""
    cols: set[str] = set()
    for check in config.quality_gates.checks:
        cols.add(check.column)

    def _filter_col(f: Filter | None) -> None:
        if f is not None:
            cols.add(f.column)

    calc = config.calculation
    # shape-specific columns (only those that are column names)
    for attr in (
        'sum_numerator_column',
        'sum_denominator_extra_column',
        'sum_numerator_subtract_column',
        'precomputed_result_column',
        'occurrence_id_column',
        'catalog_codes_column',
        'result_column',
        'name_column',
        'numerator_column',
        'denominator_column',
        'penalty_column',
    ):
        val = getattr(calc, attr, None)
        if isinstance(val, str):
            cols.add(val)
    _filter_col(getattr(calc, 'numerator_filter', None))
    _filter_col(getattr(calc, 'denominator_filter', None))
    _filter_col(getattr(calc, 'recommended_filter', None))
    _filter_col(getattr(calc, 'implemented_filter', None))
    # SegmentedRatio: list of categories
    for cat in getattr(calc, 'categories', []) or []:
        _filter_col(getattr(cat, 'numerator_filter', None))
        _filter_col(getattr(cat, 'denominator_filter', None))
    return cols


def _validate_columns(
    config: IndicatorConfig, header: set[str], config_path: Path | None
) -> None:
    missing = sorted(_collect_config_columns(config) - header)
    if missing:
        prefix = f'{config_path}: ' if config_path else ''
        raise ValueError(
            f'{prefix}coluna(s) referenciada(s) no YAML não existe(m) '
            f'no header do CSV: {", ".join(missing)} — verifique '
            f'{config_path or config.indicator.id}'
        )


def measurement_source(
    config: IndicatorConfig,
    data_dir: Path,
    manifest: DatasetManifest | None = None,
    *,
    config_path: Path | None = None,
    periodo: PeriodoAfericao | None = None,
    strict: bool = False,
    emit_period_filter_logs: bool = True,
) -> SourceBundle:
    """Backbone do pipeline de medição (ticket 02): resolve a fonte → valida
    colunas do YAML contra o header real → lê o CSV → filtra pela janela de
    período (quando *periodo* é dado) → roda os quality gates. Aditivo: não
    substitui nenhum chamador existente por si só — `engine.measure` é o
    primeiro a migrar (mesmo ticket); `sintetico`/`split`/`cli.measure`
    migram nos tickets 03-05.

    *emit_period_filter_logs* controla o WARN de janela vazia e o INFO de
    descarte fora-de-janela/sem-data (1x por dataset bruto, spec §3): o
    chamador que quer logar com seu próprio contexto estruturado (`split`,
    via `log_event`) ou que já sabe que outro ponto do mesmo `run` acabou de
    logar para este dataset (`cli.measure` quando `split` já rodou na mesma
    passada — ticket 05) passa `False` e usa as contagens no `SourceBundle`
    (`dropped_out_of_period`/`undated_dropped`) para logar por conta própria
    ou não logar de novo.
    """
    csv_path, delimiter, encoding = resolve_source(config, data_dir, manifest)
    # `read_raw_csv` (not `load_rows`): normaliza o alias "Grupo executor" ->
    # "Grupo_executor" (confirmado em produção — alguns exports usam espaço),
    # a mesma leitura que `split`/`sintetico`/`cli.measure` já faziam cada um
    # a seu jeito antes deste backbone existir.
    fieldnames, rows = read_raw_csv(csv_path, delimiter, encoding)
    header = set(fieldnames)
    # Validate every column referenced in YAML against real CSV header — single
    # border check before any strategy runs (replaces silent .get("", "") and
    # raw KeyErrors)
    _validate_columns(config, header, config_path)

    # Filtro de período (§2 ponto 2): após load_rows, inclusive CSVs `_split`
    # derivados — re-filtrar é idempotente e protege contra artefato órfão.
    # Quality gates/acceptance_test rodam sobre o pós-filtro.
    dropped_out_of_period: int | None = None
    undated_dropped: int | None = None
    if periodo is not None and not config.source.unfilterable:
        period_column = require_period_column(
            config.source.period_column, config_path=config_path
        )
        if period_column not in header:
            prefix = f'{config_path}: ' if config_path else ''
            raise ValueError(
                f'{prefix}source.period_column'
                f'{period_column!r}'
                f'não'
                f'existe'
                f'no'
                f'header'
                f'de {csv_path.name} — corrija o YAML'
            )
        total_bruto = len(rows)
        filtro = filter_periodo(
            rows, period_column=period_column, periodo=periodo, strict=strict
        )
        rows = filtro.linhas_na_janela
        dropped_out_of_period = filtro.dropped_out_of_period
        undated_dropped = filtro.undated_dropped
        if emit_period_filter_logs:
            if total_bruto > 0 and not rows:
                logger.warning(f'{csv_path}: {empty_window_message(periodo)}')
            info_descarte = discard_message(
                dropped_out_of_period or 0, undated_dropped or 0, strict
            )
            if info_descarte is not None:
                logger.info(f'{csv_path}: {info_descarte}')

    gate_runner = QualityGateRunner(
        config.quality_gates.checks, id_column=config.source.id_column
    )
    gate_report = gate_runner.run(rows)
    accepted_ids = {id(row) for row in gate_report.accepted}

    return SourceBundle(
        config=config,
        csv_path=csv_path,
        delimiter=delimiter,
        encoding=encoding,
        fieldnames=fieldnames,
        rows=rows,
        gate_report=gate_report,
        accepted_ids=accepted_ids,
        dropped_out_of_period=dropped_out_of_period,
        undated_dropped=undated_dropped,
    )


def measure(
    config: IndicatorConfig,
    data_dir: Path,
    manifest: DatasetManifest | None = None,
    *,
    config_path: Path | None = None,
    config_hash: str | None = None,
    periodo: PeriodoAfericao | None = None,
    strict: bool = False,
    emit_period_filter_logs: bool = True,
) -> MeasurementResult:
    """*config_path*/*config_hash* (the YAML this *config* was loaded from,
    and its content hash) are optional — callers that only have a
    synthetic/in-memory config (most tests) can omit them; the ROM then shows
    "Versão da configuração" as unavailable rather than requiring every
    caller to supply a path that may not exist. When *config_path* is given
    without *config_hash*, the file is re-read to hash it — the production
    path (`discover_config_files` -> `cli/measure.py`) always supplies both,
    reusing the text it already read, so this fallback only fires for direct
    callers that skip `discover_config_files`.

    *emit_period_filter_logs* repassa a decisão do backbone (ticket 05): o
    chamador que já sabe que `split` logou o WARN de janela vazia e o INFO de
    descarte para o mesmo dataset bruto na mesma passada de `run` passa
    `False` para não emitir de novo.

    Thin orchestrator (ticket 02) over `measurement_source()`: calcula e monta
    a proveniência; a resolução/leitura/filtro/gates vivem só no backbone."""
    bundle = measurement_source(
        config,
        data_dir,
        manifest,
        config_path=config_path,
        periodo=periodo,
        strict=strict,
        emit_period_filter_logs=emit_period_filter_logs,
    )

    strategy = SHAPE_REGISTRY[config.calculation.shape]
    calculation = strategy.calculate(config, bundle.gate_report.accepted)

    if config_hash is None and config_path is not None:
        config_hash = hashlib.sha256(config_path.read_bytes()).hexdigest()
    provenance = MeasurementProvenance(
        config_path=config_path,
        config_hash=config_hash,
        csv_path=bundle.csv_path,
        csv_hash=hashlib.sha256(bundle.csv_path.read_bytes()).hexdigest(),
        delimiter=bundle.delimiter,
        encoding=bundle.encoding,
        processed_at=datetime.now(),
        pipeline_version=pipeline_version(),
    )

    return MeasurementResult(
        config=config,
        quality_gate_report=bundle.gate_report,
        calculation=calculation,
        provenance=provenance,
        dropped_out_of_period=bundle.dropped_out_of_period,
        undated_dropped=bundle.undated_dropped,
    )
