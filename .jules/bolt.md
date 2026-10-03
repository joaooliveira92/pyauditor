# Bolt's Journal - Critical Learnings

## 2026-08-22 - Fast-path validation before datetime parsing
**Learning:** `datetime.strptime` is expensive when called repeatedly across large dataset rows (e.g. 100k+ entries), especially when invalid or mismatched date formats trigger `ValueError` exceptions and fallback regex checks.
**Action:** Always apply cheap length and structural character checks (`len(text) == 16` with delimiter position checks) before calling `datetime.strptime` or regex matchers on high-volume cell filtering paths.

## 2026-08-23 - Fast date construction and ABC isinstance avoidance in row loops
**Learning:** Even after length checks, `datetime.strptime` spends significant time parsing format tokens and creating intermediate `datetime` objects when only a `date` is needed (~4.3x slower than direct slicing + `date(...)`). Additionally, checking `isinstance(row, Mapping)` inside dataset loops evaluates Python ABC subclass checks (~2.5x slower than checking `type(row) is dict` first).
**Action:** Construct `date(year, month, day)` directly via string slicing after bounds validation when full datetime objects aren't required, and fast-path exact type checks (`type(x) is dict or isinstance(x, Mapping)`) inside high-volume dataset loops.

## 2026-08-24 - Pre-compiled filter predicates and set lookups in row loops
**Learning:** Evaluating filter conditions (`isinstance(filter, ColumnEquals)`) repeatedly inside high-volume row loops adds dispatch and attribute access overhead for every row in the dataset. Additionally, `ColumnIn` membership checks against list attributes (`val in in_values`) run in O(N) linear time per row.
**Action:** Pre-compile specialized closure predicates outside row iteration loops (`_build_predicate`) and convert list-based `in_values` to sets (`set(in_values)`) for O(1) hash lookups during row filtering.
