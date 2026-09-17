# Bolt's Journal - Critical Learnings

## 2026-08-22 - Fast-path validation before datetime parsing
**Learning:** `datetime.strptime` is expensive when called repeatedly across large dataset rows (e.g. 100k+ entries), especially when invalid or mismatched date formats trigger `ValueError` exceptions and fallback regex checks.
**Action:** Always apply cheap length and structural character checks (`len(text) == 16` with delimiter position checks) before calling `datetime.strptime` or regex matchers on high-volume cell filtering paths.

## 2026-08-23 - Fast date construction and ABC isinstance avoidance in row loops
**Learning:** Even after length checks, `datetime.strptime` spends significant time parsing format tokens and creating intermediate `datetime` objects when only a `date` is needed (~4.3x slower than direct slicing + `date(...)`). Additionally, checking `isinstance(row, Mapping)` inside dataset loops evaluates Python ABC subclass checks (~2.5x slower than checking `type(row) is dict` first).
**Action:** Construct `date(year, month, day)` directly via string slicing after bounds validation when full datetime objects aren't required, and fast-path exact type checks (`type(x) is dict or isinstance(x, Mapping)`) inside high-volume dataset loops.

## 2026-08-24 - Fast datetime instantiation via direct slicing & single-pass counting
**Learning:** Constructing `datetime(year, month, day, hour, minute)` via direct integer slicing of 16-char `"DD/MM/YYYY HH:MM"` strings is ~3.1x faster than `datetime.strptime(..., '%d/%m/%Y %H:%M')` (2.3s vs 7.3s for 500k ops). Furthermore, replacing separate `sum(1 for row in rows if ...)` generator calls over dataset rows with a single `for` loop pass reduces iteration overhead by 35%+.
**Action:** Use fixed-position string slicing and direct integer conversion to instantiate `datetime(...)` objects for standard format strings, and aggregate multiple counts in a single loop pass.
