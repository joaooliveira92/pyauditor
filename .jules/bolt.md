# Bolt's Journal - Critical Learnings

## 2026-08-22 - Fast-path validation before datetime parsing
**Learning:** `datetime.strptime` is expensive when called repeatedly across large dataset rows (e.g. 100k+ entries), especially when invalid or mismatched date formats trigger `ValueError` exceptions and fallback regex checks.
**Action:** Always apply cheap length and structural character checks (`len(text) == 16` with delimiter position checks) before calling `datetime.strptime` or regex matchers on high-volume cell filtering paths.

## 2026-08-23 - Fast date construction and ABC isinstance avoidance in row loops
**Learning:** Even after length checks, `datetime.strptime` spends significant time parsing format tokens and creating intermediate `datetime` objects when only a `date` is needed (~4.3x slower than direct slicing + `date(...)`). Additionally, checking `isinstance(row, Mapping)` inside dataset loops evaluates Python ABC subclass checks (~2.5x slower than checking `type(row) is dict` first).
**Action:** Construct `date(year, month, day)` directly via string slicing after bounds validation when full datetime objects aren't required, and fast-path exact type checks (`type(x) is dict or isinstance(x, Mapping)`) inside high-volume dataset loops.

## 2026-08-24 - Pre-compiled filter matcher factory and O(1) set lookup in row loops
**Learning:** Evaluating `isinstance(column_filter, ...)` and looking up filter attributes (`column`, `equals`, `in_values`, etc.) repeatedly for every row in `filter_rows` incurs significant Python object dispatch overhead. Furthermore, `ColumnIn` linear searches through `in_values` lists for every row. Pre-compiling a filter predicate closure and converting `in_values` to a `set` once before iterating yields ~3.2x faster dataset filtering.
**Action:** Always extract filter properties and convert list criteria to `set`s before starting row-level filtering loops in dataset processing strategies.
