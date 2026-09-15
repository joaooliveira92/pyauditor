# Bolt's Journal - Critical Learnings

## 2026-08-22 - Fast-path validation before datetime parsing
**Learning:** `datetime.strptime` is expensive when called repeatedly across large dataset rows (e.g. 100k+ entries), especially when invalid or mismatched date formats trigger `ValueError` exceptions and fallback regex checks.
**Action:** Always apply cheap length and structural character checks (`len(text) == 16` with delimiter position checks) before calling `datetime.strptime` or regex matchers on high-volume cell filtering paths.

## 2026-08-23 - Fast date construction and ABC isinstance avoidance in row loops
**Learning:** Even after length checks, `datetime.strptime` spends significant time parsing format tokens and creating intermediate `datetime` objects when only a `date` is needed (~4.3x slower than direct slicing + `date(...)`). Additionally, checking `isinstance(row, Mapping)` inside dataset loops evaluates Python ABC subclass checks (~2.5x slower than checking `type(row) is dict` first).
**Action:** Construct `date(year, month, day)` directly via string slicing after bounds validation when full datetime objects aren't required, and fast-path exact type checks (`type(x) is dict or isinstance(x, Mapping)`) inside high-volume dataset loops.

## 2026-08-24 - Hoisting filter type branching and set lookups in dataset loops
**Learning:** Executing Pydantic model attribute access and `isinstance(column_filter, ...)` type checks per-row inside high-volume dataset iteration loops introduces significant overhead. Pre-branching filter logic outside the row loop and converting `in_values` lists to sets once yields up to 7.4x speedup for `ColumnIn` and ~1.9x speedup for standard comparisons.
**Action:** Always resolve filter types, hoist constant attributes, and construct look-up sets outside list comprehensions when processing dataset row sequences.
