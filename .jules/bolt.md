# Bolt's Journal - Critical Learnings

## 2026-08-22 - Fast-path validation before datetime parsing
**Learning:** `datetime.strptime` is expensive when called repeatedly across large dataset rows (e.g. 100k+ entries), especially when invalid or mismatched date formats trigger `ValueError` exceptions and fallback regex checks.
**Action:** Always apply cheap length and structural character checks (`len(text) == 16` with delimiter position checks) before calling `datetime.strptime` or regex matchers on high-volume cell filtering paths.

## 2026-08-23 - Fast date construction and ABC isinstance avoidance in row loops
**Learning:** Even after length checks, `datetime.strptime` spends significant time parsing format tokens and creating intermediate `datetime` objects when only a `date` is needed (~4.3x slower than direct slicing + `date(...)`). Additionally, checking `isinstance(row, Mapping)` inside dataset loops evaluates Python ABC subclass checks (~2.5x slower than checking `type(row) is dict` first).
**Action:** Construct `date(year, month, day)` directly via string slicing after bounds validation when full datetime objects aren't required, and fast-path exact type checks (`type(x) is dict or isinstance(x, Mapping)`) inside high-volume dataset loops.

## 2026-08-24 - Pre-indexed csv.reader over csv.DictReader for high-volume CSV parsing
**Learning:** `csv.DictReader` constructs intermediate row dictionaries for every line and performs repeated key lookups (`dict.get()`) and header hashing for every cell. On 100k-row dataset files, replacing `csv.DictReader` with C-level `csv.reader` plus pre-indexed field header lists reduces CSV parsing time by ~75% (~4.1s down to ~0.97s).
**Action:** Use `csv.reader` with pre-computed field indices and direct dictionary comprehensions when reading large CSV datasets into row mappings.
