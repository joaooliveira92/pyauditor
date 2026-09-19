# Bolt's Journal - Critical Learnings

## 2026-08-22 - Fast-path validation before datetime parsing
**Learning:** `datetime.strptime` is expensive when called repeatedly across large dataset rows (e.g. 100k+ entries), especially when invalid or mismatched date formats trigger `ValueError` exceptions and fallback regex checks.
**Action:** Always apply cheap length and structural character checks (`len(text) == 16` with delimiter position checks) before calling `datetime.strptime` or regex matchers on high-volume cell filtering paths.

## 2026-08-23 - Fast date construction and ABC isinstance avoidance in row loops
**Learning:** Even after length checks, `datetime.strptime` spends significant time parsing format tokens and creating intermediate `datetime` objects when only a `date` is needed (~4.3x slower than direct slicing + `date(...)`). Additionally, checking `isinstance(row, Mapping)` inside dataset loops evaluates Python ABC subclass checks (~2.5x slower than checking `type(row) is dict` first).
**Action:** Construct `date(year, month, day)` directly via string slicing after bounds validation when full datetime objects aren't required, and fast-path exact type checks (`type(x) is dict or isinstance(x, Mapping)`) inside high-volume dataset loops.

## 2026-09-19 - Set pre-allocation and type-dispatched filtering loops
**Learning:** Re-evaluating filter types per row in `filter_rows` via dynamic dispatch or `isinstance` on every row iteration overhead adds up across 100k+ row datasets. Converting filter criteria (such as `in_values` in `ColumnIn`) to a `set` once prior to entering the list comprehension yields a ~9x speedup for `ColumnIn` and ~2x for `ColumnEquals`.
**Action:** Lift loop invariants (e.g. `set()` creation) and outer filter type checks outside row list comprehensions in high-volume row filtering utilities.
