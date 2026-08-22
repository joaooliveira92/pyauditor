"""Acesso a arquivos/CSV do pipeline de medição (ticket 02 backbone).

Extraído de `engine/pipeline.py` (ticket 03 SRP): resolução de fonte
(manifest/dataset ou `csv` legado), detecção de delimiter divergente
(fato de produção 2026-06) e leitura bruta em `dict`. A normalização do
header `Grupo executor` → `Grupo_executor` vive em `categoria_filter`
(`read_raw_csv`), porque `categoria_filter` é folha (só importa `config`)
e `engine.loading` já depende dela para o backbone.
"""

from __future__ import annotations

import csv
from pathlib import Path

from pyauditor.categoria_filter import read_raw_csv
from pyauditor.config.manifest import DatasetManifest
from pyauditor.config.models import IndicatorConfig
from pyauditor.logging import logger

__all__ = (
    'load_rows',
    'read_raw_csv',
    'resolve_source',
)

_DELIMITER_CANDIDATES: tuple[str, ...] = (',', ';')


def load_rows(
    source_path: Path, delimiter: str, encoding: str
) -> list[dict[str, str]]:
    with source_path.open(encoding=encoding, newline='') as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        if reader.fieldnames is None:
            raise ValueError(
                f'{source_path}: CSV vazio ou sem linha de cabeçalho'
            )
        fieldnames = [name.strip() for name in reader.fieldnames]
        reader.fieldnames = fieldnames
        # Real-world rows are occasionally ragged (free-text fields containing
        # the delimiter shift columns) — DictReader stuffs overflow into a
        # `None` key holding a list; only the declared columns are kept.
        return [
            {name: (row.get(name) or '').strip() for name in fieldnames}
            for row in reader
        ]


def _detect_delimiter(csv_path: Path, encoding: str, configured: str) -> str:
    """O manifest/config declara um delimiter fixo por dataset, mas exports
    mensais às vezes divergem por arquivo (confirmado em produção, 2026-06:
    `datasets.yaml` da MTur declara `;` para todos os 14 datasets, mas 3
    arquivos daquele mês vieram com `,`). Lê só a linha de cabeçalho e troca
    para o delimiter mais provável quando o configurado não aparece nela —
    nunca lança: se o arquivo não existe ou não pode ser lido, o erro real
    aparece no ponto de leitura de verdade (`load_rows`/`read_raw_csv`)."""
    if configured not in _DELIMITER_CANDIDATES:
        # delimiter incomum e explícito — respeita, não tenta adivinhar
        return configured
    try:
        with csv_path.open(encoding=encoding, newline='') as handle:
            header = handle.readline()
    except OSError:
        return configured
    if configured in header:
        return configured
    detected = next(
        (c for c in _DELIMITER_CANDIDATES if c != configured and c in header),
        None,
    )
    if detected is None:
        return configured
    logger.warning(
        f'{csv_path}: delimiter configurado {configured!r} não aparece no'
        f'cabeçalho, '
        f'usando {detected!r} (detectado) — corrija o manifest/config se isso'
        f'persistir'
    )
    return detected


def resolve_source(
    config: IndicatorConfig,
    data_dir: Path,
    manifest: DatasetManifest | None,
) -> tuple[Path, str, str]:
    """Resolve the CSV path + parsing options from the indicator's source
    config.

    Public (not `measure()`-only) — `cli/split.py` also resolves a base
    indicator's raw source before filtering it per Categoria.

    Returns:
        (csv_path, delimiter, encoding)
    """
    source = config.source
    if source.dataset is not None:
        if manifest is None:
            raise ValueError(
                f'{config.indicator.id}: source.dataset={source.dataset!r} '
                'requires a manifest, but none was provided'
            )
        entry = manifest.resolve(source.dataset)
        csv_path = data_dir / entry.file
        delimiter = _detect_delimiter(csv_path, entry.encoding, entry.delimiter)
        return csv_path, delimiter, entry.encoding
    # Legacy: direct csv filename
    if source.csv is None:  # guaranteed by Source model validator
        raise ValueError('source.csv não pode ser None no ramo legado')
    csv_path = data_dir / source.csv
    delimiter = _detect_delimiter(csv_path, source.encoding, source.delimiter)
    return csv_path, delimiter, source.encoding
