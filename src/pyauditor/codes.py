"""User-facing contractual code formatting.

The canonical `indicator.contractual_id` (e.g. ``"INMS 1.1"``) is a stable
internal key: grouping, sorting and decision-matching all key on it verbatim.
But the *displayed* form zero-pads the minor version so codes read naturally
to humans — ``INMS 1.1`` renders as ``INMS 1.01`` while ``INMS 1.10`` and
``INMS 1.14`` are unchanged. Only codes shaped like ``INMS <n>.<m>`` are
touched; anything else passes through untouched (e.g. synthetic ``"INMS TEST"``).
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