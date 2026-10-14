# Bolt's Journal - Critical Learnings

## 2026-08-22 - Fast-path validation before datetime parsing
**Learning:** `datetime.strptime` is expensive when called repeatedly across large dataset rows (e.g. 100k+ entries), especially when invalid or mismatched date formats trigger `ValueError` exceptions and fallback regex checks.
**Action:** Always apply cheap length and structural character checks (`len(text) == 16` with delimiter position checks) before calling `datetime.strptime` or regex matchers on high-volume cell filtering paths.

## 2026-08-23 - Fast date construction and ABC isinstance avoidance in row loops
**Learning:** Even after length checks, `datetime.strptime` spends significant time parsing format tokens and creating intermediate `datetime` objects when only a `date` is needed (~4.3x slower than direct slicing + `date(...)`). Additionally, checking `isinstance(row, Mapping)` inside dataset loops evaluates Python ABC subclass checks (~2.5x slower than checking `type(row) is dict` first).
**Action:** Construct `date(year, month, day)` directly via string slicing after bounds validation when full datetime objects aren't required, and fast-path exact type checks (`type(x) is dict or isinstance(x, Mapping)`) inside high-volume dataset loops.

## 2026-08-24 - Fast direct datetime construction for DD/MM/YYYY HH:MM and DD/MM/YYYY
**Learning:** `datetime.strptime(text, '%d/%m/%Y %H:%M')` spends significant CPU time parsing format string specifiers even when length and structural character checks pass (~4.3x slower than direct string slicing with `int()` and `datetime(...)`).
**Action:** Replace `datetime.strptime` in high-volume cell date parsing paths (`parse_dt`, `parse_datahora`, `_parse_data_br`) with direct `datetime(int(s[6:10]), int(s[3:5]), int(s[:2]), ...)` after verifying exact length and delimiter positions (`/`, `:`, `' '`), with fallback to `strptime`.
