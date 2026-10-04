# Bolt's Journal - Critical Learnings

## 2026-08-22 - Fast-path validation before datetime parsing
**Learning:** `datetime.strptime` is expensive when called repeatedly across large dataset rows (e.g. 100k+ entries), especially when invalid or mismatched date formats trigger `ValueError` exceptions and fallback regex checks.
**Action:** Always apply cheap length and structural character checks (`len(text) == 16` with delimiter position checks) before calling `datetime.strptime` or regex matchers on high-volume cell filtering paths.

## 2026-08-23 - Fast date construction and ABC isinstance avoidance in row loops
**Learning:** Even after length checks, `datetime.strptime` spends significant time parsing format tokens and creating intermediate `datetime` objects when only a `date` is needed (~4.3x slower than direct slicing + `date(...)`). Additionally, checking `isinstance(row, Mapping)` inside dataset loops evaluates Python ABC subclass checks (~2.5x slower than checking `type(row) is dict` first).
**Action:** Construct `date(year, month, day)` directly via string slicing after bounds validation when full datetime objects aren't required, and fast-path exact type checks (`type(x) is dict or isinstance(x, Mapping)`) inside high-volume dataset loops.

## 2026-08-24 - Hash map grouping over repeated linear filters in sheet renderers
**Learning:** Repeating list comprehensions (`[row for row in rows if row[col] == group]`) inside category/group loops scales quadratically $O(N \cdot G)$ as row count $N$ and group count $G$ grow. A pre-pass hash map `defaultdict(list)` groups dataset rows in $O(N)$ time and speeds up Excel sheet rendering by over ~3.4x on 100k-row datasets.
**Action:** Always pre-group dataset rows into a dictionary (`rows_by_group = defaultdict(list)`) before iterating over groups or categories in report generator loops.
