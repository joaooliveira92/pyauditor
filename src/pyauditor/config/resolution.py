"""Resolve configuration directories and dataset manifests consistently.

This module provides the canonical resolution strategy shared by all
application entry points.

Resolution follows ADR 0003:

1. Use ``<base>/_shared`` when it exists as a directory.
2. Otherwise, use ``<base>/<orgao>``.
3. Resolve ``datasets.yaml`` from the selected configuration directory.

Keeping this logic in one module prevents commands from selecting configuration
files from different roots for the same organization.

It also owns the per-órgão expansion (ticket 12): `cli/main.py` e
`orchestration/run.py` derivam os caminhos por órgão de uma única fonte
(`per_orgao_paths`) em vez de cada um reimplementar a expansão com sémântica
própria.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

from pyauditor.config.manifest import DatasetManifest, load_manifest

__all__: Final[tuple[str, ...]] = (
    "PerOrgaoPaths",
    "load_manifest_for",
    "per_orgao_paths",
    "resolve_config_dir",
    "resolve_manifest_path",
)

_MANIFEST_FILENAME: Final[str] = "datasets.yaml"
_SHARED_DIRNAME: Final[str] = "_shared"


def resolve_config_dir(base: Path, orgao: str) -> Path:
    """Resolve the canonical configuration directory for an organization.

    The shared configuration directory takes precedence when it exists.
    Otherwise, the organization-specific directory is returned. The returned
    fallback path is not required to exist.

    Args:
        base: Root directory containing shared and organization configurations.
        orgao: Organization directory name used when no shared directory exists.

    Returns:
        The shared configuration directory or the organization-specific
        fallback path.
    """
    shared = base / _SHARED_DIRNAME
    if shared.is_dir():
        return shared
    return base / orgao


def resolve_manifest_path(base: Path, orgao: str) -> Path:
    """Resolve the dataset manifest path for an organization.

    The manifest path is derived from the canonical configuration directory so
    that all entry points use the same configuration root.

    Args:
        base: Root directory containing configuration directories.
        orgao: Organization directory name used when no shared directory exists.

    Returns:
        The expected path to the canonical ``datasets.yaml`` file.
    """
    return resolve_config_dir(base, orgao) / _MANIFEST_FILENAME


def load_manifest_for(base: Path, orgao: str) -> DatasetManifest | None:
    """Load the canonical dataset manifest for an organization.

    Args:
        base: Root directory containing configuration directories.
        orgao: Organization directory name used when no shared directory exists.

    Returns:
        The loaded dataset manifest, or ``None`` when the resolved manifest is
        not a regular file.

    Raises:
        Exception: Propagates errors raised by ``load_manifest`` when the file
            cannot be read, parsed, or validated.
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