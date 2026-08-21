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

from pyauditor.config.manifest import DatasetManifest, load_manifest
from pyauditor.config.models import IndicatorConfig
from pyauditor.engine.quality_gates import QualityGateReport, QualityGateRunner
from pyauditor.engine.strategies import SHAPE_REGISTRY
from pyauditor.engine.strategies.base import CalculationResult


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
class MeasurementResult:
    config: IndicatorConfig
    quality_gate_report: QualityGateReport
    calculation: CalculationResult
    provenance: MeasurementProvenance

    @property
    def hard_failure(self) -> bool:
        """Quality gates rejected every row that existed — not the same as a source
        CSV that had zero rows to begin with (a legitimately empty competência,
        e.g. INMS 1.3/1.8/1.9/1.10 before manual data entry exists)."""
        report = self.quality_gate_report
        return len(report.accepted) == 0 and len(report.rejected) > 0


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
            capture_output=True, text=True, timeout=5, check=True,
        )
        return result.stdout.strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return "dev"


def load_config(config_path: Path) -> IndicatorConfig:
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
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
        return csv_path, entry.delimiter, entry.encoding
    # Legacy: direct csv filename
    assert source.csv is not None  # guaranteed by Source model validator
    csv_path = data_dir / source.csv
    return csv_path, source.delimiter, source.encoding


def discover_config_files(
    config_dir: Path, expected_orgao: str | None = None
) -> list[tuple[Path, str, IndicatorConfig]]:
    """Same discovery as `discover_configs`, but keeps each config's source
    path and content hash alongside it — `measure()`'s provenance needs both,
    computed here (while `raw_text` is in hand) rather than re-reading the
    file a second time. `discover_configs` can't gain these without breaking
    its existing `list[IndicatorConfig]` callers."""
    triples: list[tuple[Path, str, IndicatorConfig]] = []
    for path in sorted(config_dir.glob("*.yaml")):
        raw_text = path.read_text(encoding="utf-8")
        raw = yaml.safe_load(raw_text)
        if not isinstance(raw, dict) or "indicator" not in raw:
            # Not an indicator config (e.g. `datasets.yaml`, the manifest that
            # now lives alongside the indicators) — skip it.
            continue
        config = IndicatorConfig.model_validate(raw)
        if expected_orgao is not None and config.scope.orgao != expected_orgao:
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


def measure(
    config: IndicatorConfig,
    data_dir: Path,
    manifest: DatasetManifest | None = None,
    *,
    config_path: Path | None = None,
    config_hash: str | None = None,
) -> MeasurementResult:
    """*config_path*/*config_hash* (the YAML this *config* was loaded from,
    and its content hash) are optional — callers that only have a
    synthetic/in-memory config (most tests) can omit them; the ROM then shows
    "Versão da configuração" as unavailable rather than requiring every
    caller to supply a path that may not exist. When *config_path* is given
    without *config_hash*, the file is re-read to hash it — the production
    path (`discover_config_files` -> `cli/measure.py`) always supplies both,
    reusing the text it already read, so this fallback only fires for direct
    callers that skip `discover_config_files`."""
    csv_path, delimiter, encoding = resolve_source(config, data_dir, manifest)
    rows = load_rows(csv_path, delimiter, encoding)

    gate_runner = QualityGateRunner(config.quality_gates.checks, id_column=config.source.id_column)
    gate_report = gate_runner.run(rows)

    strategy = SHAPE_REGISTRY[config.calculation.shape]
    calculation = strategy.calculate(config, gate_report.accepted)

    if config_hash is None and config_path is not None:
        config_hash = hashlib.sha256(config_path.read_bytes()).hexdigest()
    provenance = MeasurementProvenance(
        config_path=config_path,
        config_hash=config_hash,
        csv_path=csv_path,
        csv_hash=hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        delimiter=delimiter,
        encoding=encoding,
        processed_at=datetime.now(),
        pipeline_version=_pipeline_version(),
    )

    return MeasurementResult(
        config=config,
        quality_gate_report=gate_report,
        calculation=calculation,
        provenance=provenance,
    )
