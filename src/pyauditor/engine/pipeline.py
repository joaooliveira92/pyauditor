"""Orchestrates one indicator's measurement: parse config -> load CSV -> quality
gates -> calculation strategy -> ROM-ready result.
"""

import csv
from dataclasses import dataclass
from pathlib import Path

import yaml

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
        """Quality gates rejected every row — no data survived to measure against."""
        return len(self.quality_gate_report.accepted) == 0


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


def discover_configs(config_dir: Path) -> list[IndicatorConfig]:
    return [load_config(path) for path in sorted(config_dir.glob("*.yaml"))]


def measure(config: IndicatorConfig, data_dir: Path) -> MeasurementResult:
    rows = load_rows(data_dir / config.source.csv, config.source.delimiter, config.source.encoding)

    gate_runner = QualityGateRunner(config.quality_gates.checks, id_column=config.source.id_column)
    gate_report = gate_runner.run(rows)

    strategy = SHAPE_REGISTRY[config.calculation.shape]
    calculation = strategy.calculate(config, gate_report.accepted)

    return MeasurementResult(config=config, quality_gate_report=gate_report, calculation=calculation)
