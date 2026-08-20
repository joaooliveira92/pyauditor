"""Atomic file writes — write to a temp file in the same directory, then
`os.replace()` into place, so a crash mid-write (power loss, killed process)
can never leave a truncated/corrupt file at the final path. Matters most for
files a later run reads back (a consolidado workbook, the glosa ledger) —
one bad write shouldn't brick the next run's ability to read it.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from pathlib import Path


def atomic_write(path: Path, write: Callable[[Path], object]) -> None:
    """Calls `write(tmp_path)` against a temp file beside *path*, then
    replaces *path* with it. On any exception, the temp file is removed and
    *path* is left untouched."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        write(tmp_path)
        os.replace(tmp_path, path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise
