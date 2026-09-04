# Bolt's Journal - Critical Learnings

## 2026-08-22 - Fast-path validation before datetime parsing
**Learning:** `datetime.strptime` is expensive when called repeatedly across large dataset rows (e.g. 100k+ entries), especially when invalid or mismatched date formats trigger `ValueError` exceptions and fallback regex checks.
**Action:** Always apply cheap length and structural character checks (`len(text) == 16` with delimiter position checks) before calling `datetime.strptime` or regex matchers on high-volume cell filtering paths.

## 2026-09-04 - Direct integer extraction bypasses `strptime` for 4x speedup
**Learning:** Even with fast-path structure checks, `datetime.strptime` incurs noticeable C-overhead and creates intermediate `datetime` objects when only `date` is needed. Extracting date/time integers (`int(text[6:10])`, etc.) directly for fixed 16-character strings (`"DD/MM/YYYY HH:MM"`) is ~4x faster than `strptime`.
**Action:** For known fixed-format date strings, extract components via slice + `int()` and construct `date(...)` / `datetime(...)` directly after validating bounds.
