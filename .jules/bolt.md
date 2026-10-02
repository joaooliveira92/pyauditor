# Bolt's Journal - Critical Learnings

## 2026-08-22 - Fast-path validation before datetime parsing
**Learning:** `datetime.strptime` is expensive when called repeatedly across large dataset rows (e.g. 100k+ entries), especially when invalid or mismatched date formats trigger `ValueError` exceptions and fallback regex checks.
**Action:** Always apply cheap length and structural character checks (`len(text) == 16` with delimiter position checks) before calling `datetime.strptime` or regex matchers on high-volume cell filtering paths.

## 2026-08-23 - Fast date construction and ABC isinstance avoidance in row loops
**Learning:** Even after length checks, `datetime.strptime` spends significant time parsing format tokens and creating intermediate `datetime` objects when only a `date` is needed (~4.3x slower than direct slicing + `date(...)`). Additionally, checking `isinstance(row, Mapping)` inside dataset loops evaluates Python ABC subclass checks (~2.5x slower than checking `type(row) is dict` first).
**Action:** Construct `date(year, month, day)` directly via string slicing after bounds validation when full datetime objects aren't required, and fast-path exact type checks (`type(x) is dict or isinstance(x, Mapping)`) inside high-volume dataset loops.

## 2026-08-24 - Pre-convert ColumnIn filter lists to sets and fast-path type dispatch in row loops
**Learning:** Membership checking `value in column_filter.in_values` evaluates a linear list scan O(M) for every dataset row, causing significant slowdowns (e.g. ~280ms vs ~25ms on 200k rows) when filtering indicator datasets. Hoisting target values and converting filter candidate lists to `set` instances before dataset row loops yields an ~11x speedup.
**Action:** Always hoist attribute lookups and pre-convert candidate lists to `set` instances outside row-filtering list comprehensions.
