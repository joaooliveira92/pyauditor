"""Origem/versão do pipeline usada na proveniência dos ROMs.

Extraído de `engine/pipeline.py` (ticket 03 SRP): a versão instalada do
pacote com fallback para o commit git e, por fim, um marcador fixo. Público
(`pipeline_version`) — `cli/measure.py` usava o `_pipeline_version` privado.
"""

from __future__ import annotations

import functools
import importlib.metadata
import subprocess
from typing import Final

__all__: Final[tuple[str, ...]] = ("pipeline_version",)


@functools.lru_cache(maxsize=1)
def pipeline_version() -> str:
    """Installed package version, falling back to the git commit for
    non-installed (source tree) execution, and finally a fixed marker."""
    try:
        return importlib.metadata.version("pyauditor")
    except importlib.metadata.PackageNotFoundError:
        pass
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        return result.stdout.strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return "dev"