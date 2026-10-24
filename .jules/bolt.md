# Bolt's Journal - Critical Learnings

## 2026-08-22 - Fast-path validation before datetime parsing
**Learning:** `datetime.strptime` is expensive when called repeatedly across large dataset rows (e.g. 100k+ entries), especially when invalid or mismatched date formats trigger `ValueError` exceptions and fallback regex checks.
**Action:** Always apply cheap length and structural character checks (`len(text) == 16` with delimiter position checks) before calling `datetime.strptime` or regex matchers on high-volume cell filtering paths.

## 2026-08-23 - Fast date construction and ABC isinstance avoidance in row loops
**Learning:** Even after length checks, `datetime.strptime` spends significant time parsing format tokens and creating intermediate `datetime` objects when only a `date` is needed (~4.3x slower than direct slicing + `date(...)`). Additionally, checking `isinstance(row, Mapping)` inside dataset loops evaluates Python ABC subclass checks (~2.5x slower than checking `type(row) is dict` first).
**Action:** Construct `date(year, month, day)` directly via string slicing after bounds validation when full datetime objects aren't required, and fast-path exact type checks (`type(x) is dict or isinstance(x, Mapping)`) inside high-volume dataset loops.

## 2026-08-24 - Pre-building predicate closures and set lookups for row filtering
**Learning:** Evaluating `isinstance(column_filter, ...)` and attribute accesses inside dataset row filtering loops adds significant overhead (~1.4x for equality checks, up to ~6.6x for `ColumnIn` when scanning lists). Pre-building a specialized predicate closure once before filtering and using `set` for `in_values` eliminates per-row dispatch and converts linear list searches to $O(1)$ set lookups.
**Action:** When filtering row streams with static config criteria, construct specialized predicate closures and pre-convert collection filters to sets outside the iteration loop.
