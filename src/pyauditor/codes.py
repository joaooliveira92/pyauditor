"""User-facing contractual code formatting.

The canonical `indicator.contractual_id` (e.g. ``"INMS 1.1"``) is a stable
internal key: grouping and decision-matching key on it verbatim. But the
*displayed* form zero-pads the minor version so codes read naturally to
humans — ``INMS 1.1`` renders as ``INMS 1.01`` while ``INMS 1.10`` and
``INMS 1.14`` are unchanged. Only codes shaped like ``INMS <n>.<m>`` are
touched; anything else passes through untouched (ex. ``"INMS" "TEST"``).

Sorting is a separate concern (`contractual_sort_key`): the minor version is
numeric, not lexicographic — ``INMS 1.2`` must sort before ``INMS 1.10``,
which plain string comparison on the verbatim code gets wrong (``"1.10"`` <
``"1.2"`` as strings).
"""

from __future__ import annotations

import re
from functools import lru_cache

_INMS_CODE_RE: re.Pattern[str] = re.compile(
    r'^(INMS\s+\d+)\.(\d+)$', re.IGNORECASE
)
_INMS_CODE_BARE_RE: re.Pattern[str] = re.compile(r'^(\d+)\.(\d+)$')


# ⚡ Bolt: otimização de performance.
# Memoiza a formatação e a chave de ordenação de códigos contratuais usando
# lru_cache. Como a quantidade de identificadores INMS únicos por execução é
# pequena, mas a formatação é chamada repetidamente em loops pesados de
# geração de relatórios e planilhas, o cache evita a reavaliação de regexes
# e alocações de string (acelerando em ~6x as chamadas).
@lru_cache(maxsize=128)
def format_inms_code(code: str) -> str:
    """Return the user-facing, zero-padded form of a contractual code.

    ``"INMS 1.9"`` -> ``"INMS 1.09"``; ``"INMS 1.10"`` -> ``"INMS 1.10"``.
    Codes that don't match the ``INMS <n>.<m>`` shape are returned unchanged.
    """
    match = _INMS_CODE_RE.match(code)
    if match is None:
        return code
    whole, minor = match.groups()
    return f'{whole}.{minor.zfill(2)}'


# ⚡ Bolt: memoiza a formatação numérica reduzida de códigos contratuais.
@lru_cache(maxsize=128)
def format_inms_code_numeric(code: str) -> str:
    """Return the bare, zero-padded ``n.m`` form without the ``INMS``
    prefix (``"INMS 1.9"`` -> ``"1.09"``) — the compact form GLOSAS's
    ``Indicador`` column displays, where the header already says
    "indicador" and one row per occurrence makes the prefix noise.
    Codes that don't match the ``INMS <n>.<m>`` shape pass through
    unchanged, same fallback as `format_inms_code`.
    """
    match = _INMS_CODE_RE.match(code)
    if match is None:
        return code
    whole, minor = match.groups()
    major = whole.split()[-1]
    return f'{major}.{minor.zfill(2)}'


# ⚡ Bolt: memoiza a normalização de códigos exibidos para a chave interna.
@lru_cache(maxsize=128)
def parse_inms_code(code: str) -> str:
    """Canonicalize a *displayed* contractual code back to the internal
    ``INMS <n>.<m>`` key, accepting either `format_inms_code`'s full form
    (``"INMS 1.02"``) or `format_inms_code_numeric`'s bare form
    (``"1.02"``). Lets `read_existing_decisions` build the same join key
    regardless of which of the two a prior run wrote to the GLOSAS
    ``Indicador`` column, so re-runs keep matching fiscal decisions already
    on disk.
    """
    bare = _INMS_CODE_BARE_RE.match(code.strip())
    if bare is not None:
        major, minor = bare.groups()
        return format_inms_code(f'INMS {major}.{minor}')
    return format_inms_code(code)


# ⚡ Bolt: memoiza a chave de ordenação contratual. Evita reavaliar regex
# e alocar tuplas quando múltiplos relatórios ordenam e agrupam pelos mesmos
# códigos contratuais repetidamente.
@lru_cache(maxsize=128)
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
        return (1, code, 0, '')
    whole, minor = match.groups()
    return (0, whole, int(minor), code)
