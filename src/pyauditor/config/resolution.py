"""Resolve configuration directories and dataset manifests consistently.

This module provides the canonical resolution strategy shared by all
application entry points.

Resolution follows ADR 0003:

1. Use ``<base>/_shared`` when it exists as a directory.
2. Otherwise, use ``<base>/<orgao>``.
3. Resolve ``datasets.yaml`` from the selected configuration directory.

Keeping this logic in one module prevents commands from selecting configuration
files from different roots for the same organization.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from pyauditor.config.manifest import DatasetManifest, load_manifest

__all__: Final[tuple[str, ...]] = (
    "load_manifest_for",
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