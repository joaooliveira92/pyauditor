# Bolt's Journal - Critical Learnings

## 2026-08-22 - Fast-path validation before datetime parsing
**Learning:** `datetime.strptime` is expensive when called repeatedly across large dataset rows (e.g. 100k+ entries), especially when invalid or mismatched date formats trigger `ValueError` exceptions and fallback regex checks.
**Action:** Always apply cheap length and structural character checks (`len(text) == 16` with delimiter position checks) before calling `datetime.strptime` or regex matchers on high-volume cell filtering paths.

## 2026-08-23 - Fast date construction and ABC isinstance avoidance in row loops
**Learning:** Even after length checks, `datetime.strptime` spends significant time parsing format tokens and creating intermediate `datetime` objects when only a `date` is needed (~4.3x slower than direct slicing + `date(...)`). Additionally, checking `isinstance(row, Mapping)` inside dataset loops evaluates Python ABC subclass checks (~2.5x slower than checking `type(row) is dict` first).
**Action:** Construct `date(year, month, day)` directly via string slicing after bounds validation when full datetime objects aren't required, and fast-path exact type checks (`type(x) is dict or isinstance(x, Mapping)`) inside high-volume dataset loops.

## 2026-10-21 - Filter type hoisting and set conversion in row filtering loops
**Learning:** Calling `_matches` inside `filter_rows` for every row introduces inner-loop function dispatch overhead and repeated `isinstance` evaluations. Furthermore, evaluating `value in column_filter.in_values` with a list does an $O(M)$ scan for every row ($O(N \times M)$ total). Hoisting `isinstance` type checks outside the row loop and pre-converting `in_values` to a `set` ($O(1)$) yields a ~5.7x speedup on dataset filtering.
**Action:** Inspect filter type once outside row loops in dataset filtering functions, and pre-convert candidate collections (`in_values`) to sets before iterating over rows.
