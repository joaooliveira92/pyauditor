"""Orchestrates one indicator's measurement: parse config -> load CSV -> quality
gates -> calculation strategy -> ROM-ready result.
"""

import csv
import functools
import hashlib
import importlib.metadata
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml

from pyauditor.config.manifest import DatasetManifest
from pyauditor.config.models import Filter, IndicatorConfig
from pyauditor.engine.quality_gates import QualityGateReport, QualityGateRunner
from pyauditor.engine.strategies import SHAPE_REGISTRY
from pyauditor.engine.strategies.base import CalculationResult
from pyauditor.logging import logger
from pyauditor.periodo import (
    PeriodoAfericao,
    discard_message,
    empty_window_message,
    filter_periodo,
    require_period_column,
)

_DELIMITER_CANDIDATES: tuple[str, ...] = (",", ";")


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
        """Quality gates rejected every row that existed — not the same as a source
        CSV that had zero rows to begin with (a legitimately empty competência,
        e.g. INMS 1.3/1.8/1.9/1.10 before manual data entry exists)."""
        report = self.quality_gate_report
        return len(report.accepted) == 0 and len(report.rejected) > 0

    @property
    def systematic_failure(self) -> bool:
        """Não-conformidade sistemática/estrutural: o cálculo rodou sem erro
        mas está sempre não-conforme com resultado extremo (0%). Distinto de
        não-conformidade pontual/esperada, que continua não sendo hard_failure."""
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
        if isinstance(calc, PrecomputedTableCalculation) and not calc.result_is_percent:
            return False
        return self.calculation.result_pct == 0.0


@functools.lru_cache(maxsize=1)
def _pipeline_version() -> str:
    """Installed package version, falling back to the git commit for
    non-installed (source tree) execution, and finally a fixed marker."""
    try:
        return importlib.metadata.version("pyauditor")
    except importlib.metadata.PackageNotFoundError:
        pass
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        return result.stdout.strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return "dev"


def _collect_config_columns(config: IndicatorConfig) -> set[str]:
    """All column names referenced in *config* that must exist in the CSV header.
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
        "sum_numerator_column",
        "sum_denominator_extra_column",
        "sum_numerator_subtract_column",
        "precomputed_result_column",
        "occurrence_id_column",
        "catalog_codes_column",
        "result_column",
        "name_column",
        "numerator_column",
        "denominator_column",
        "penalty_column",
    ):
        val = getattr(calc, attr, None)
        if isinstance(val, str):
            cols.add(val)
    _filter_col(getattr(calc, "numerator_filter", None))
    _filter_col(getattr(calc, "denominator_filter", None))
    _filter_col(getattr(calc, "recommended_filter", None))
    _filter_col(getattr(calc, "implemented_filter", None))
    # SegmentedRatio: list of categories
    for cat in getattr(calc, "categories", []) or []:
        _filter_col(getattr(cat, "numerator_filter", None))
        _filter_col(getattr(cat, "denominator_filter", None))
    return cols


def _validate_columns(config: IndicatorConfig, header: set[str], config_path: Path | None) -> None:
    missing = sorted(_collect_config_columns(config) - header)
    if missing:
        prefix = f"{config_path}: " if config_path else ""
        raise ValueError(
            f"{prefix}coluna(s) referenciada(s) no YAML não existe(m) no header do CSV: "
            f"{', '.join(missing)} — verifique {config_path or config.indicator.id}"
        )


def load_config(config_path: Path) -> IndicatorConfig:
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "indicator" not in raw:
        # Detect typo like `indicador:` — instead of silently skipping later
        for key in raw:
            if isinstance(key, str) and key.strip().lower() in (
                "indicador",
                "indicators",
                "indicatior",
            ):
                raise ValueError(
                    f"{config_path}: chave {key!r} encontrada, esperado 'indicator:' — "
                    "typo no YAML, corrija a chave"
                )
        # also check if file looks like an indicator config (inms-*.yaml) but missing key
        if config_path.name.startswith("inms-"):
            raise ValueError(
                f"{config_path}: chave 'indicator:' ausente — "
                "arquivo não é config válida de indicador"
            )
    return IndicatorConfig.model_validate(raw)


def load_rows(source_path: Path, delimiter: str, encoding: str) -> list[dict[str, str]]:
    with source_path.open(encoding=encoding, newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        if reader.fieldnames is None:
            raise ValueError(f"{source_path}: CSV vazio ou sem linha de cabeçalho")
        fieldnames = [name.strip() for name in reader.fieldnames]
        reader.fieldnames = fieldnames
        # Real-world rows are occasionally ragged (free-text fields containing
        # the delimiter shift columns) — DictReader stuffs overflow into a
        # `None` key holding a list; only the declared columns are kept.
        return [{name: (row.get(name) or "").strip() for name in fieldnames} for row in reader]


def _detect_delimiter(csv_path: Path, encoding: str, configured: str) -> str:
    """O manifest/config declara um delimiter fixo por dataset, mas exports
    mensais às vezes divergem por arquivo (confirmado em produção, 2026-06:
    `datasets.yaml` da MTur declara `;` para todos os 14 datasets, mas 3
    arquivos daquele mês vieram com `,`). Lê só a linha de cabeçalho e troca
    para o delimiter mais provável quando o configurado não aparece nela —
    nunca lança: se o arquivo não existe ou não pode ser lido, o erro real
    aparece no ponto de leitura de verdade (`load_rows`/`read_raw_csv`)."""
    if configured not in _DELIMITER_CANDIDATES:
        return configured  # delimiter incomum e explícito — respeita, não tenta adivinhar
    try:
        with csv_path.open(encoding=encoding, newline="") as handle:
            header = handle.readline()
    except OSError:
        return configured
    if configured in header:
        return configured
    detected = next((c for c in _DELIMITER_CANDIDATES if c != configured and c in header), None)
    if detected is None:
        return configured
    logger.warning(
        f"{csv_path}: delimiter configurado {configured!r} não aparece no cabeçalho, "
        f"usando {detected!r} (detectado) — corrija o manifest/config se isso persistir"
    )
    return detected


def resolve_source(
    config: IndicatorConfig,
    data_dir: Path,
    manifest: DatasetManifest | None,
) -> tuple[Path, str, str]:
    """Resolve the CSV path + parsing options from the indicator's source config.

    Public (not `measure()`-only) — `cli/split.py` also resolves a base
    indicator's raw source before filtering it per Categoria.

    Returns:
        (csv_path, delimiter, encoding)
    """
    source = config.source
    if source.dataset is not None:
        if manifest is None:
            raise ValueError(
                f"{config.indicator.id}: source.dataset={source.dataset!r} "
                "requires a manifest, but none was provided"
            )
        entry = manifest.resolve(source.dataset)
        csv_path = data_dir / entry.file
        delimiter = _detect_delimiter(csv_path, entry.encoding, entry.delimiter)
        return csv_path, delimiter, entry.encoding
    # Legacy: direct csv filename
    assert source.csv is not None  # guaranteed by Source model validator
    csv_path = data_dir / source.csv
    delimiter = _detect_delimiter(csv_path, source.encoding, source.delimiter)
    return csv_path, delimiter, source.encoding


_ORGAO_CONTRACT: dict[str, str] = {
    "MinC": "40/2022 - Ministério da Cultura",
    "MTur": "40/2022 - Ministério do Turismo",
}


def _inject_orgao(config: IndicatorConfig, expected_orgao: str) -> IndicatorConfig:
    """Injeta `scope.orgao`/`contract` quando o YAML vem de `configs/_shared/`."""
    desired_contract = _ORGAO_CONTRACT.get(expected_orgao, config.scope.contract)
    if config.scope.orgao == expected_orgao and config.scope.contract == desired_contract:
        return config
    from pyauditor.config.models import Scope

    new_scope = Scope(contract=desired_contract, orgao=expected_orgao)  # type: ignore[arg-type]
    return config.model_copy(update={"scope": new_scope})


def discover_config_files(
    config_dir: Path, expected_orgao: str | None = None
) -> list[tuple[Path, str, IndicatorConfig]]:
    """Same discovery as `discover_configs`, but keeps each config's source
    path and content hash alongside it — `measure()`'s provenance needs both,
    computed here (while `raw_text` is in hand) rather than re-reading the
    file a second time. `discover_configs` can't gain these without breaking
    its existing `list[IndicatorConfig]` callers.

    Quando `expected_orgao` é informado e o arquivo vem de `configs/_shared/`
    (single-source), o `scope` é injetado em runtime em vez de validar
    mismatch — o YAML canônico não carrega `scope` por órgão.
    """
    triples: list[tuple[Path, str, IndicatorConfig]] = []
    is_shared = config_dir.name == "_shared" or (config_dir / "_shared").exists()
    for path in sorted(config_dir.glob("*.yaml")):
        raw_text = path.read_text(encoding="utf-8")
        raw = yaml.safe_load(raw_text)
        if not isinstance(raw, dict) or "indicator" not in raw:
            # Detect typo in indicator key before silently skipping
            if isinstance(raw, dict):
                for key in raw:
                    if isinstance(key, str) and key.strip().lower() in (
                        "indicador",
                        "indicators",
                        "indicatior",
                        "indicator ",
                    ):
                        raise ValueError(
                            f"{path}: chave {key!r} encontrada, esperado 'indicator:' — "
                            "typo no YAML"
                        )
                if path.name.startswith("inms-"):
                    raise ValueError(
                        f"{path}: chave 'indicator:' ausente — "
                        "arquivo não é config válida de indicador"
                    )
            # Not an indicator config (e.g. `datasets.yaml`, the manifest that
            # now lives alongside the indicators) — skip it.
            continue
        config = IndicatorConfig.model_validate(raw)
        if expected_orgao is not None:
            # Single-source: injetar órgão/contrato em vez de falhar.
            if is_shared or config_dir.name == "_shared":
                config = _inject_orgao(config, expected_orgao)
            elif config.scope.orgao != expected_orgao:
                raise ValueError(
                    f"{path}: scope.orgao={config.scope.orgao!r} não corresponde ao "
                    f"órgão solicitado {expected_orgao!r} — config no diretório errado"
                )
        content_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
        triples.append((path, content_hash, config))
    return triples


def discover_configs(config_dir: Path, expected_orgao: str | None = None) -> list[IndicatorConfig]:
    """Load every indicator config from *config_dir* (one per `*.yaml`,
    skipping non-indicator manifests like `datasets.yaml`).

    When *expected_orgao* is given, every config whose ``scope.orgao`` differs
    is a hard error (per-conf layout is per-órgão: `configs/<órgão>/`).
    """
    return [config for _, _, config in discover_config_files(config_dir, expected_orgao)]


def measurement_source(
    config: IndicatorConfig,
    data_dir: Path,
    manifest: DatasetManifest | None = None,
    *,
    config_path: Path | None = None,
    periodo: PeriodoAfericao | None = None,
    strict: bool = False,
    emit_empty_window_warning: bool = True,
) -> SourceBundle:
    """Backbone do pipeline de medição (ticket 02): resolve a fonte → valida
    colunas do YAML contra o header real → lê o CSV → filtra pela janela de
    período (quando *periodo* é dado) → roda os quality gates. Aditivo: não
    substitui nenhum chamador existente por si só — `engine.measure` é o
    primeiro a migrar (mesmo ticket); `sintetico`/`split`/`cli.measure`
    migram nos tickets 03-05.

    *emit_empty_window_warning* controla o WARN de janela vazia (1x por
    dataset bruto, spec §3): o chamador que já sabe que outro ponto do mesmo
    `run` acabou de emiti-lo para este dataset (ex.: `cli.measure` quando
    `split` já rodou na mesma passada — ticket 05) passa `False` para não
    duplicar o aviso. O INFO de descarte fora-de-janela/sem-data é sempre
    emitido — não é o aviso duplicado, é contagem informativa por chamada.
    """
    csv_path, delimiter, encoding = resolve_source(config, data_dir, manifest)
    # Validate every column referenced in YAML against real CSV header — single
    # border check before any strategy runs (replaces silent .get("", "") and raw KeyErrors)
    with csv_path.open(encoding=encoding, newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        if reader.fieldnames is None:
            raise ValueError(f"{csv_path}: CSV vazio ou sem linha de cabeçalho")
        fieldnames = [name.strip() for name in reader.fieldnames]
        header = set(fieldnames)
    _validate_columns(config, header, config_path)

    rows = load_rows(csv_path, delimiter, encoding)

    # Filtro de período (§2 ponto 2): após load_rows, inclusive CSVs `_split`
    # derivados — re-filtrar é idempotente e protege contra artefato órfão.
    # Quality gates/acceptance_test rodam sobre o pós-filtro.
    dropped_out_of_period: int | None = None
    undated_dropped: int | None = None
    if periodo is not None and not config.source.unfilterable:
        period_column = require_period_column(config.source.period_column, config_path=config_path)
        if period_column not in header:
            prefix = f"{config_path}: " if config_path else ""
            raise ValueError(
                f"{prefix}source.period_column {period_column!r} não existe no header "
                f"de {csv_path.name} — corrija o YAML"
            )
        total_bruto = len(rows)
        filtro = filter_periodo(rows, period_column=period_column, periodo=periodo, strict=strict)
        rows = filtro.linhas_na_janela
        dropped_out_of_period = filtro.dropped_out_of_period
        undated_dropped = filtro.undated_dropped
        if emit_empty_window_warning and total_bruto > 0 and not rows:
            logger.warning(f"{csv_path}: {empty_window_message(periodo)}")
        info_descarte = discard_message(dropped_out_of_period or 0, undated_dropped or 0, strict)
        if info_descarte is not None:
            logger.info(f"{csv_path}: {info_descarte}")

    gate_runner = QualityGateRunner(config.quality_gates.checks, id_column=config.source.id_column)
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

    Thin orchestrator (ticket 02) over `measurement_source()`: calcula e monta
    a proveniência; a resolução/leitura/filtro/gates vivem só no backbone."""
    bundle = measurement_source(
        config,
        data_dir,
        manifest,
        config_path=config_path,
        periodo=periodo,
        strict=strict,
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
        pipeline_version=_pipeline_version(),
    )

    return MeasurementResult(
        config=config,
        quality_gate_report=bundle.gate_report,
        calculation=calculation,
        provenance=provenance,
        dropped_out_of_period=bundle.dropped_out_of_period,
        undated_dropped=bundle.undated_dropped,
    )
