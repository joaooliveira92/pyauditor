"""Derivação de atefatos por `(INMS, categoria)` para `cli/split` (ticket 08
SRP). São as funções puras (sem I/O de workbook/sintetico) que `run_split`
usa: escrita atômica do CSV filtrado, derivação da config do indicador e
escrita da config derivada. A orquestração fica em `cli/split.py`.
"""

from __future__ import annotations

import csv
from pathlib import Path

import yaml

from pyauditor.atomic_write import atomic_write
from pyauditor.config.models import IndicatorConfig, Source

__all__: tuple[str, ...] = (
    'derive_config',
    'write_derived_config',
    'write_filtered_csv',
)


def write_filtered_csv(
    path: Path,
    fieldnames: list[str],
    rows: list[dict[str, str]],
    delimiter: str,
) -> None:
    """Write a filtered CSV atomically."""

    def _write(tmp_path: Path) -> None:
        with tmp_path.open('w', encoding='utf-8', newline='') as handle:
            writer = csv.DictWriter(
                handle, fieldnames=fieldnames, delimiter=delimiter
            )
            writer.writeheader()
            writer.writerows(rows)

    atomic_write(path, _write)


def derive_config(
    base: IndicatorConfig,
    categoria_key: str,
    csv_relpath: str | None = None,
    delimiter: str | None = None,
) -> IndicatorConfig:
    """Copia `quality_gates`/`calculation`/`target`/`penalty` de *base*,
    trocando só `indicator.id`. `acceptance_test` (números do dataset
    inteiro) não se aplica ao subconjunto filtrado — omitido.

    `csv_relpath`/`delimiter` materializam `source` apontando pro CSV
    filtrado em disco (`split`, nunca `source.dataset` — `split` não toca
    em `datasets.yaml`). Omitidos (default), a config derivada mantém o
    `source` de *base* — o caminho em memória (`measure`/categorias)
    filtra as linhas do CSV bruto já lido, sem escrever nada."""
    derived_indicator = base.indicator.model_copy(
        update={'id': f'{base.indicator.id}.{categoria_key}'}
    )
    update: dict[str, object] = {
        'indicator': derived_indicator,
        'acceptance_test': None,
    }
    if csv_relpath is not None:
        update['source'] = Source(
            csv=csv_relpath,
            delimiter=delimiter or base.source.delimiter,
            encoding='utf-8',
            id_column=base.source.id_column,
            period_column=base.source.period_column,
        )
    return base.model_copy(update=update)


def write_derived_config(path: Path, config: IndicatorConfig) -> None:
    raw = config.model_dump(mode='json', exclude_none=True)

    def _write(tmp_path: Path) -> None:
        tmp_path.write_text(
            yaml.safe_dump(raw, allow_unicode=True, sort_keys=False),
            encoding='utf-8',
        )

    atomic_write(path, _write)
