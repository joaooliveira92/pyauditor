"""User-facing contractual code formatting.

The canonical `indicator.contractual_id` (e.g. ``"INMS 1.1"``) is a stable
internal key: grouping and decision-matching key on it verbatim. But the
*displayed* form zero-pads the minor version so codes read naturally to
humans — ``INMS 1.1`` renders as ``INMS 1.01`` while ``INMS 1.10`` and
``INMS 1.14`` are unchanged. Only codes shaped like ``INMS <n>.<m>`` are
touched; anything else passes through untouched (e.g. synthetic ``"INMS TEST"``).

Sorting is a separate concern (`contractual_sort_key`): the minor version is
numeric, not lexicographic — ``INMS 1.2`` must sort before ``INMS 1.10``,
which plain string comparison on the verbatim code gets wrong (``"1.10"`` <
``"1.2"`` as strings).
"""

from __future__ import annotations

import re

_INMS_CODE_RE: re.Pattern[str] = re.compile(r"^(INMS\s+\d+)\.(\d+)$", re.IGNORECASE)


def format_inms_code(code: str) -> str:
    """Return the user-facing, zero-padded form of a contractual code.

    ``"INMS 1.9"`` -> ``"INMS 1.09"``; ``"INMS 1.10"`` -> ``"INMS 1.10"``.
    Codes that don't match the ``INMS <n>.<m>`` shape are returned unchanged.
    """
    match = _INMS_CODE_RE.match(code)
    if match is None:
        return code
    whole, minor = match.groups()
    return f"{whole}.{minor.zfill(2)}"


def contractual_sort_key(code: str) -> tuple[int, str, int, str]:
    """Sort key that orders ``INMS <n>.<m>`` codes numerically by ``m``
    (``INMS 1.2`` before ``INMS 1.10``) instead of lexicographically.

    Codes that don't match the ``INMS <n>.<m>`` shape sort after every
    matching code (first tuple element ``1`` vs. ``0``), ordered among
    themselves by the raw string, so callers get a stable, deterministic
    order without needing to special-case them.
    """
    match = _INMS_CODE_RE.match(code)
    if match is None:
        return (1, code, 0, "")
    whole, minor = match.groups()
    return (0, whole, int(minor), code)