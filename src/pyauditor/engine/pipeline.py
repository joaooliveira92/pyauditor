"""Orchestrates one indicator's measurement: parse config -> load CSV -> quality
gates -> calculation strategy -> ROM-ready result.
"""

import csv
from dataclasses import dataclass
from pathlib import Path

import yaml

from pyauditor.config.manifest import DatasetManifest, load_manifest
from pyauditor.config.models import IndicatorConfig
from pyauditor.engine.quality_gates import QualityGateReport, QualityGateRunner
from pyauditor.engine.strategies import SHAPE_REGISTRY
from pyauditor.engine.strategies.base import CalculationResult

@dataclass(frozen=True)
class MeasurementResult:
    config: IndicatorConfig
    quality_gate_report: QualityGateReport
    calculation: CalculationResult

    @property
    def hard_failure(self) -> bool:
        """Quality gates rejected every row that existed — not the same as a source
        CSV that had zero rows to begin with (a legitimately empty competência,
        e.g. INMS 1.3/1.8/1.9/1.10 before manual data entry exists)."""
        report = self.quality_gate_report
        return len(report.accepted) == 0 and len(report.rejected) > 0


def load_config(config_path: Path) -> IndicatorConfig:
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return IndicatorConfig.model_validate(raw)


def load_rows(source_path: Path, delimiter: str, encoding: str) -> list[dict[str, str]]:
    with source_path.open(encoding=encoding, newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        assert reader.fieldnames is not None
        fieldnames = [name.strip() for name in reader.fieldnames]
        reader.fieldnames = fieldnames
        # Real-world rows are occasionally ragged (free-text fields containing
        # the delimiter shift columns) — DictReader stuffs overflow into a
        # `None` key holding a list; only the declared columns are kept.
        return [{name: (row.get(name) or "").strip() for name in fieldnames} for row in reader]


def _resolve_source(
    config: IndicatorConfig,
    data_dir: Path,
    manifest: DatasetManifest | None,
) -> tuple[Path, str, str]:
    """Resolve the CSV path + parsing options from the indicator's source config.

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


def discover_configs(config_dir: Path, expected_orgao: str | None = None) -> list[IndicatorConfig]:
    """Load every indicator config from *config_dir* (one per `*.yaml`,
    skipping non-indicator manifests like `datasets.yaml`).

    When *expected_orgao* is given, every config whose ``scope.orgao`` differs
    is a hard error (per-conf layout is per-órgão: `configs/<órgão>/`).
    """
    configs: list[IndicatorConfig] = []
    for path in sorted(config_dir.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
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
        configs.append(config)
    return configs


def measure(
    config: IndicatorConfig,
    data_dir: Path,
    manifest: DatasetManifest | None = None,
) -> MeasurementResult:
    csv_path, delimiter, encoding = _resolve_source(config, data_dir, manifest)
    rows = load_rows(csv_path, delimiter, encoding)

    gate_runner = QualityGateRunner(config.quality_gates.checks, id_column=config.source.id_column)
    gate_report = gate_runner.run(rows)

    strategy = SHAPE_REGISTRY[config.calculation.shape]
    calculation = strategy.calculate(config, gate_report.accepted)

    return MeasurementResult(config=config, quality_gate_report=gate_report, calculation=calculation)
