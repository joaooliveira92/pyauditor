"""Module-level registry of calculation strategies, keyed by `shape` (spec §9).

Also re-exports the small pure helpers every strategy shares
(`_filters`/`_numbers`/`_target`) as the one public seam for callers outside
this package — `excel/sintetico.py` used to reach past it into the
underscore-prefixed submodules directly (ticket 03); import these instead of
`pyauditor.engine.strategies._filters` etc.
"""

from pyauditor.engine.strategies._filters import filter_rows
from pyauditor.engine.strategies._numbers import as_float, parse_decimal
from pyauditor.engine.strategies._registry import SHAPE_REGISTRY
from pyauditor.engine.strategies._target import (
    meets_target,
    safe_pct,
    shortfall,
)
from pyauditor.engine.strategies.penalty import (
    PenaltyReadings,
    penalty_interpretation,
)

__all__ = (
    'SHAPE_REGISTRY',
    'PenaltyReadings',
    'as_float',
    'filter_rows',
    'meets_target',
    'parse_decimal',
    'penalty_interpretation',
    'safe_pct',
    'shortfall',
)
