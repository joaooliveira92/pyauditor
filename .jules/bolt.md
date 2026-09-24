# Bolt's Journal - Critical Learnings

## 2026-08-22 - Fast-path validation before datetime parsing
**Learning:** `datetime.strptime` is expensive when called repeatedly across large dataset rows (e.g. 100k+ entries), especially when invalid or mismatched date formats trigger `ValueError` exceptions and fallback regex checks.
**Action:** Always apply cheap length and structural character checks (`len(text) == 16` with delimiter position checks) before calling `datetime.strptime` or regex matchers on high-volume cell filtering paths.

## 2026-08-23 - Fast date construction and ABC isinstance avoidance in row loops
**Learning:** Even after length checks, `datetime.strptime` spends significant time parsing format tokens and creating intermediate `datetime` objects when only a `date` is needed (~4.3x slower than direct slicing + `date(...)`). Additionally, checking `isinstance(row, Mapping)` inside dataset loops evaluates Python ABC subclass checks (~2.5x slower than checking `type(row) is dict` first).
**Action:** Construct `date(year, month, day)` directly via string slicing after bounds validation when full datetime objects aren't required, and fast-path exact type checks (`type(x) is dict or isinstance(x, Mapping)`) inside high-volume dataset loops.

## 2026-09-24 - Avoid Worksheet.max_column inside openpyxl row insertion loops
**Learning:** `openpyxl.worksheet.worksheet.Worksheet.max_column` iterates over all keys in `Worksheet._cells` on every access (`max(c[1] for c in self._cells)`). Accessing `sheet.max_column` per row inside row-writing loops converts $O(N \cdot C)$ row insertions into an $O(N^2 \cdot C)$ quadratic bottleneck as the cell dictionary grows.
**Action:** Cache the expected column count on the `Worksheet` object (e.g. `_pyauditor_expected_columns`) during sheet initialization or on first access to make row schema validation $O(1)$.
