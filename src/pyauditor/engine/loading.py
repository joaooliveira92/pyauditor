"""Acesso a arquivos/CSV do pipeline de medição (ticket 02 backbone).

Extraído de `engine/pipeline.py` (ticket 03 SRP): resolução de fonte
(manifest/dataset ou `csv` legado), detecção de delimiter divergente
(fato de produção 2026-06) e leitura bruta em `dict`. A normalização do
header `Grupo executor` → `Grupo_executor` vive em `categoria_filter`
(`read_raw_csv`), porque `categoria_filter` é folha (só importa `config`)
e `engine.loading` já depende dela para o backbone.
"""

from __future__ import annotations

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
# Amostra de linhas de dados (além da cabecera) para conferir o delimiter —
# a cabecera sozinha engana quando um nome de campo contém o outro candidato.
_DELIMITER_SAMPLE_ROWS: int = 20


def load_rows(
    source_path: Path, delimiter: str, encoding: str
) -> list[dict[str, str]]:
    """Delega no leitor canônico único (`read_raw_csv`): remove espaços dos
    nomes de coluna, normaliza o alias `Grupo_executor` e conta linhas
    ragged. Wrapper fino mantido para os chamadores que só precisam das
    filas (sem anomalias)."""
    return read_raw_csv(source_path, delimiter, encoding).rows


def _detect_delimiter(
    csv_path: Path,
    encoding: str,
    configured: str,
    *,
    strict: bool = False,
) -> str:
    """O manifest/config declara um delimiter fixo por dataset, mas exports
    mensais às vezes divergem por arquivo (confirmado em produção, 2026-06:
    `datasets.yaml` da MTur declara `;` para todos os 14 datasets, mas 3
    arquivos daquele mês vieram com `,`).

    Decide pelo candidato com mais ocorrências na cabecera **e numa amostra
    de linhas de dados** (não só na cabecera — um nome de campo contendo o
    outro candidato enganaria a leitura só de cabecera). Troca para o
    vencedor quando diverge do configurado (warning); em empate/ausência
    total, `strict` falha com `ValueError` e o modo normal mantém o
    configurado com warning forte. Nunca lança por arquivo ilegível: o erro
    real aparece no ponto de leitura de verdade (`read_raw_csv`)."""
    if configured not in _DELIMITER_CANDIDATES:
        # delimiter incomum e explícito — respeita, não tenta adivinhar
        return configured
    try:
        with csv_path.open(encoding=encoding, newline='') as handle:
            linhas = [handle.readline()]
            for _ in range(_DELIMITER_SAMPLE_ROWS):
                linha = handle.readline()
                if not linha:
                    break
                linhas.append(linha)
    except OSError:
        return configured

    contagens = {
        cand: sum(linha.count(cand) for linha in linhas)
        for cand in _DELIMITER_CANDIDATES
    }
    vencedor = max(contagens, key=contagens.__getitem__)
    empatados = [
        cand
        for cand, total in contagens.items()
        if total == contagens[vencedor]
    ]
    if len(empatados) == 1 and vencedor != configured:
        logger.warning(
            f'{csv_path}: delimiter configurado {configured!r} não aparece no '
            f'conteúdo real, usando {vencedor!r} (detectado) — corrija o '
            f'manifest/config se isso persistir'
        )
        return vencedor
    if len(empatados) == 1:
        return configured
    # Ambíguo: ambos os candidatos aparecem ou nenhum aparece na amostra.
    if strict:
        raise ValueError(
            f'{csv_path}: delimiter ambíguo entre {", ".join(contagens)} na '
            f'cabecera/amostra de dados — configure o delimiter correto no '
            f'manifest/config'
        )
    logger.warning(
        f'{csv_path}: delimiter ambíguo entre {", ".join(contagens)} na '
        f'cabecera/amostra de dados — mantendo o configurado {configured!r}; '
        f'confira o resultado'
    )
    return configured


def resolve_source(
    config: IndicatorConfig,
    data_dir: Path,
    manifest: DatasetManifest | None,
    *,
    strict: bool = False,
) -> tuple[Path, str, str]:
    """Resolve o caminho do CSV + opções de parsing a partir do source da
    config do indicador.

    Pública (não só de `measure()`) — `cli/split.py` também resolve o source
    bruto de um indicador base antes de filtrá-lo por Categoria.

    *strict* propaga para a detecção de delimiter: um delimiter ambíguo vira
    `ValueError` duro em vez de chute best-effort.

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
        delimiter = _detect_delimiter(
            csv_path, entry.encoding, entry.delimiter, strict=strict
        )
        return csv_path, delimiter, entry.encoding
    # Legacy: direct csv filename
    if source.csv is None:  # guaranteed by Source model validator
        raise ValueError('source.csv não pode ser None no ramo legado')
    csv_path = data_dir / source.csv
    delimiter = _detect_delimiter(
        csv_path, source.encoding, source.delimiter, strict=strict
    )
    return csv_path, delimiter, source.encoding
