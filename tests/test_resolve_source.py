"""`engine.loading.resolve_source` — a decisão de fonte (ticket 03).

Cobre: ramo dataset via manifest, ramo CSV legado, manifest ausente com
`dataset` declarado → erro acionável, e o delimiter divergente no ponto de
decisão do chamador (troca pelo detectado quando o configurado não aparece no
cabeçalho; mutismo — mantém o configurado — quando não há candidato).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyauditor.config.manifest import DatasetEntry, DatasetManifest
from pyauditor.config.models import (
    ColumnEquals,
    Indicator,
    IndicatorConfig,
    QualityGates,
    RatioCalculation,
    Source,
    Target,
)
from pyauditor.engine.loading import resolve_source


def _config(source: Source) -> IndicatorConfig:
    return IndicatorConfig(
        indicator=Indicator(
            id='INMS-1.1', contractual_id='INMS 1.1', name='Teste'
        ),
        source=source,
        quality_gates=QualityGates(),
        calculation=RatioCalculation(
            shape='ratio',
            aggregation='count_distinct',
            numerator_filter=ColumnEquals(column='Atendido', equals='S'),
        ),
        target=Target(operator='>=', value=90.0),
    )


def _manifest() -> DatasetManifest:
    return DatasetManifest(
        {
            'telefonemas': DatasetEntry(
                file='dados.csv', delimiter=';', encoding='utf-8'
            )
        }
    )


def test_dataset_branch_resolves_manifest_entry(tmp_path: Path) -> None:
    manifest = _manifest()
    (tmp_path / 'dados.csv').write_text('a;b\n1;2\n', encoding='utf-8')
    config = _config(Source(dataset='telefonemas'))

    csv_path, delimiter, encoding = resolve_source(config, tmp_path, manifest)

    assert csv_path == tmp_path / 'dados.csv'
    assert delimiter == ';'
    assert encoding == 'utf-8'


def test_legacy_csv_branch_resolves_source(tmp_path: Path) -> None:
    (tmp_path / 'legado.csv').write_text('a,b\n1,2\n', encoding='utf-8')
    config = _config(Source(csv='legado.csv', delimiter=',', encoding='utf-8'))

    csv_path, delimiter, encoding = resolve_source(config, tmp_path, None)

    assert csv_path == tmp_path / 'legado.csv'
    assert delimiter == ','
    assert encoding == 'utf-8'


def test_missing_manifest_with_dataset_raises_actionable_error() -> None:
    config = _config(Source(dataset='telefonemas'))

    with pytest.raises(ValueError, match='requires a manifest'):
        resolve_source(config, Path('.'), None)


def test_dataset_branch_switches_to_detected_delimiter(
    tmp_path: Path,
) -> None:
    """Fato de produção 2026-06 no ponto de decisão do chamador: o manifest
    declara `;` mas o arquivo veio com `,` — `resolve_source` troca."""
    manifest = _manifest()
    (tmp_path / 'dados.csv').write_text('a,b\n1,2\n', encoding='utf-8')
    config = _config(Source(dataset='telefonemas'))

    _, delimiter, _ = resolve_source(config, tmp_path, manifest)

    assert delimiter == ','


def test_legacy_branch_switches_to_detected_delimiter(
    tmp_path: Path,
) -> None:
    (tmp_path / 'legado.csv').write_text('a;b\n1;2\n', encoding='utf-8')
    config = _config(Source(csv='legado.csv', delimiter=',', encoding='utf-8'))

    _, delimiter, _ = resolve_source(config, tmp_path, None)

    assert delimiter == ';'


def test_keeps_configured_delimiter_when_no_candidate_in_header(
    tmp_path: Path,
) -> None:
    """Sem candidato no cabeçalho (nem `;` nem `,`) o chamador mantém o
    configurado — mutismo, nunca chuta."""
    manifest = _manifest()
    (tmp_path / 'dados.csv').write_text('a b\n1 2\n', encoding='utf-8')
    config = _config(Source(dataset='telefonemas'))

    _, delimiter, _ = resolve_source(config, tmp_path, manifest)

    assert delimiter == ';'


def test_legacy_branch_keeps_configured_delimiter_when_no_candidate(
    tmp_path: Path,
) -> None:
    (tmp_path / 'legado.csv').write_text('a b\n1 2\n', encoding='utf-8')
    config = _config(Source(csv='legado.csv', delimiter=',', encoding='utf-8'))

    _, delimiter, _ = resolve_source(config, tmp_path, None)

    assert delimiter == ','
