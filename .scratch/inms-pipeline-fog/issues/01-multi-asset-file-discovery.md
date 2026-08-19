# 01 — Multi-asset file discovery for per-asset indicators

**What to build:** `measure` and `report` handle multiple YAML+CSV pairs sharing one contractual indicator number, so a fiscal técnico measuring INMS 1.14 across its 6 named infrastructure services (File Server, Telefonia, Mensageria, Servidores de impressão, WI-FI, Rede — Anexo D) gets one ROM and one `INMS_BASE` row per service, not a collision or a silent overwrite.

Per `docs/spec/inms-pipeline.md` §2.1 (ticket 13's decision), a per-asset indicator like 1.4/1.5/1.14 is already "um YAML+CSV = um ativo/serviço = uma medição independente" — this ticket is about *discovering and consolidating* several such independent measurements under the same contractual indicator number, which today only works by accident if the config/output filenames happen not to collide.

**Blocked by:** None — can start immediately

**Status:** resolved

- [x] Config naming convention for multiple assets under one indicator is defined and documented (e.g. `inms-1.14-file-server.yaml`, `inms-1.14-wifi.yaml`) — each carries its own `contractual_id: "INMS 1.14"` plus an asset label
- [x] `measure` writes one ROM + one JSON summary per asset, with filenames that can't collide across assets of the same indicator
- [x] `report`'s `INMS_BASE` shows one row per asset (not deduplicated to the indicator number), each row identifying which asset/serviço it measures
- [x] Group tabs (`MONITORAMENTO_NOC_SOC`, etc.) list every asset row for indicators that have them
- [x] A synthetic fixture with 2+ assets under the same indicator number proves discovery, ROM/summary generation, and `INMS_BASE`/group-tab rows all handle the multi-asset case without collision
- [x] `mypy --strict` passes

## Answer

- `Indicator` (`config/models.py`) gained an optional `asset: str | None` field — the value that distinguishes measurements sharing one `contractual_id`. `None` for ordinary single-asset indicators; a human-readable label (e.g. `"File Server"`, `"WI-FI"`) for per-asset ones. `indicator.id` stays the actual uniqueness guarantee for filenames (unchanged mechanism — `cli/measure.py`'s existing sanitize-and-write-by-id logic already didn't collide once ids differ; the missing piece was giving each asset a *displayable* identity, not a new collision-avoidance mechanism).
- Naming convention adopted and documented (in the fixture comments and now in `docs/spec/inms-pipeline.md` §13): `inms-<n>-<asset-slug>.yaml`, distinct `indicator.id` per file, shared `contractual_id`, `indicator.asset` set to the label.
- `rom/summary.py`'s `IndicatorSummary` gained `asset: str | None`, threaded through from `config.indicator.asset`.
- `rom/render.py`'s ROM title now appends `" — {asset}"` when present, e.g. `# ROM — INMS 1.14 — WI-FI (...)`.
- `excel/report.py`: `INMS_BASE`'s "Serviço" column (previously always blank/fiscal-manual) is now filled from `summary.asset` when present. Group tabs (`_GROUP_TAB_COLUMNS`) gained a "Serviço" column too, so two rows for the same indicator are visually distinguishable, not just numerically different. Sorting changed from `contractual_id` alone to `(contractual_id, asset)` for a stable, grouped-by-indicator order.
- **What did *not* need to change:** `discover_configs`/`measure`/`cli/report.py`'s `_load_summaries` already iterate per config file, not per `contractual_id` — there was no deduplication logic to remove. The "collision" risk was purely about output filenames (already solved by distinct `id`s) and about the Excel output being unreadable without a way to tell two same-indicator rows apart (now solved by `asset`).
- `tests/fixtures/multi_asset_configs/` (new, separate from the canonical `tests/fixtures/configs/` — keeps `test_full_acceptance_smoke.py`'s "exactly 14 real indicators" assertion untouched) holds two synthetic INMS 1.14 configs (File Server 99.80%, WI-FI 98.90% — one conforming, one not, to prove independent results). `tests/test_multi_asset_discovery.py` proves: `discover_configs` finds both; `measure` writes 4 distinct files (2 ROM + 2 JSON) with no collision; `INMS_BASE` and `MONITORAMENTO_NOC_SOC` each show 2 rows with correct per-asset results.

Verified: `uv run mypy --strict src tests` → `Success: no issues found in 50 source files`. `uv run pytest -q` → `106 passed`. Also ran the full `bootstrap → measure → report` pipeline via the installed CLI against the 2 synthetic multi-asset configs — 2 distinct ROMs generated, `MONITORAMENTO_NOC_SOC` correctly shows both (File Server conforme, WI-FI não conforme, 1500 pontos).
