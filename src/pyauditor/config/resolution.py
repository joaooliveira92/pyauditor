"""Resolução canônica de diretórios de configuração e manifest de datasets,
compartilhada por todos os pontos de entrada da aplicação (ticket 01).

A precedência segue o ADR 0003:

1. Usa ``<base>/_shared`` quando existir como diretório.
2. Senão, usa ``<base>/<orgao>``.
3. Resolve ``datasets.yaml`` a partir do diretório de configuração escolhido.

Centralizar esta lógica num módulo impede que comandos escolham raízes de
configuração diferentes para o mesmo órgão.

O módulo também é dono da expansão per-órgão (ticket 12): `cli/main.py` e
`orchestration/run.py` derivam os caminhos por órgão de uma única fonte
(`per_orgao_paths`) em vez de cada um reimplementar a expansão com semântica
própria.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

from pyauditor.config.manifest import DatasetManifest, load_manifest

__all__: Final[tuple[str, ...]] = (
    'PerOrgaoPaths',
    'load_manifest_for',
    'per_orgao_paths',
    'resolve_config_dir',
    'resolve_manifest_path',
)

_MANIFEST_FILENAME: Final[str] = 'datasets.yaml'
_SHARED_DIRNAME: Final[str] = '_shared'


def resolve_config_dir(base: Path, orgao: str) -> Path:
    """Diretório de configuração canônico de um órgão.

    O diretório compartilhado tem precedência quando existe; senão, devolve o
    diretório do órgão. O caminho de fallback não precisa existir.
    """
    shared = base / _SHARED_DIRNAME
    if shared.is_dir():
        return shared
    return base / orgao


def resolve_manifest_path(base: Path, orgao: str) -> Path:
    """Caminho do manifest de datasets de um órgão.

    Derivado do diretório de configuração canônico, para todos os pontos de
    entrada usarem a mesma raiz de configuração.
    """
    return resolve_config_dir(base, orgao) / _MANIFEST_FILENAME


def load_manifest_for(base: Path, orgao: str) -> DatasetManifest | None:
    """Carrega o manifest canônico de datasets de um órgão.

    Devolve ``None`` quando o manifest resolvido não é um arquivo regular.
    Propaga os erros de ``load_manifest`` quando o arquivo não pode ser lido,
    parseado ou validado.
    """
    path = resolve_manifest_path(base, orgao)
    if not path.is_file():
        return None
    return load_manifest(path)


@dataclass(frozen=True, slots=True)
class PerOrgaoPaths:
    """Derived per-órgão paths shared by every consumer of the expansion.

    ``config_dir`` é o diretório de configurações canônico do órgão (via
    ADR 0003); ``data_dir``/``output_dir`` são as raízes anexadas com
    ``/ <orgao>``; ``manifest`` é o manifest do órgão (``None`` quando a
    resolução não é um arquivo regular). ``report_dir`` só existe quando o
    chamador tem uma raiz de relatórios per-órgão (ex.: o ``split``).
    """

    config_dir: Path
    data_dir: Path
    output_dir: Path
    manifest: DatasetManifest | None
    report_dir: Path | None = None


def per_orgao_paths(
    *,
    config_dir: Path,
    data_dir: Path,
    output_dir: Path,
    orgao: str,
    report_dir: Path | None = None,
) -> PerOrgaoPaths:
    """Compute the canonical per-órgão paths + manifest (ticket 12).

    Only the per-órgão variance lives here: the config root, data root and
    output root are passed in exactly as the caller received them (the base,
    before the ``/ <orgao>`` suffix); this resolver applies the órgão once so
    `main` e `run` can't diverge de novo. ``config_dir`` resolves com a regra
    única de precedência (ADR 0003) e qualquer ``report_dir`` informado vira
    uma raiz per-órgão própria.
    """
    return PerOrgaoPaths(
        config_dir=resolve_config_dir(config_dir, orgao),
        data_dir=data_dir / orgao,
        output_dir=output_dir / orgao,
        manifest=load_manifest_for(config_dir, orgao),
        report_dir=report_dir / orgao if report_dir is not None else None,
    )
