# Bolt's Journal - Critical Learnings

## 2026-08-22 - Fast-path validation before datetime parsing
**Learning:** `datetime.strptime` is expensive when called repeatedly across large dataset rows (e.g. 100k+ entries), especially when invalid or mismatched date formats trigger `ValueError` exceptions and fallback regex checks.
**Action:** Always apply cheap length and structural character checks (`len(text) == 16` with delimiter position checks) before calling `datetime.strptime` or regex matchers on high-volume cell filtering paths.

## 2026-09-05 - Avoid per-row isinstance dispatch and linear lookups in row filters
**Learning:** Evaluating `isinstance` on every row during dataset iteration introduces significant dispatch overhead. Additionally, `in_values` sequence lookups inside loops perform linear O(K) scans per row, and duration parsers using generator expressions create iterator allocations for every row.
**Action:** Dispatch filter type once before looping, convert `in_values` to `set` for O(1) lookups, and unpack fixed tuple splits directly instead of generator expressions in tight row-processing loops.
