# Bolt's Journal - Critical Learnings

## 2026-08-22 - Fast-path validation before datetime parsing
**Learning:** `datetime.strptime` is expensive when called repeatedly across large dataset rows (e.g. 100k+ entries), especially when invalid or mismatched date formats trigger `ValueError` exceptions and fallback regex checks.
**Action:** Always apply cheap length and structural character checks (`len(text) == 16` with delimiter position checks) before calling `datetime.strptime` or regex matchers on high-volume cell filtering paths.

## 2026-08-23 - Fast date construction and ABC isinstance avoidance in row loops
**Learning:** Even after length checks, `datetime.strptime` spends significant time parsing format tokens and creating intermediate `datetime` objects when only a `date` is needed (~4.3x slower than direct slicing + `date(...)`). Additionally, checking `isinstance(row, Mapping)` inside dataset loops evaluates Python ABC subclass checks (~2.5x slower than checking `type(row) is dict` first).
**Action:** Construct `date(year, month, day)` directly via string slicing after bounds validation when full datetime objects aren't required, and fast-path exact type checks (`type(x) is dict or isinstance(x, Mapping)`) inside high-volume dataset loops.

## 2026-08-24 - Direct datetime constructor for DD/MM/YYYY HH:MM and single-pass stats computation
**Learning:** Calling `datetime.strptime(text, "%d/%m/%Y %H:%M")` incurs heavy format-string parsing overhead (~4.5x slower than direct `datetime(year, month, day, hour, minute)` construction from string slices after character/delimiter validation). Furthermore, calculating stats over datasets in separate `sum()` passes multiplies iteration overhead over high-volume row lists.
**Action:** Fast-path fixed format `"DD/MM/YYYY HH:MM"` strings directly to `datetime(int(...), ...)` constructor after length and delimiter checks, and consolidate dataset statistics computation into a single pass over `rows`.
