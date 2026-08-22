"""Shared path-safety validator for config-declared filenames (`Source.csv`,
`DatasetEntry.file`) — rejects absolute paths and `..` segments so a
malicious/malformed config can't escape the data directory it's resolved
against (`data_dir / entry.file`)."""

from __future__ import annotations

from pathlib import PurePosixPath, PureWindowsPath


def reject_unsafe_relative_path(value: str) -> str:
    for path_cls in (PurePosixPath, PureWindowsPath):
        candidate = path_cls(value)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ValueError(f"{value!r} must be a relative filename with no '..' segments")
    return value
