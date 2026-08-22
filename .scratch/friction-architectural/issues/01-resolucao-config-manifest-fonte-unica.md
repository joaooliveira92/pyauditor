# 01 — Resolução `configs/_shared` + manifest em fonte única

**What to build:** um único resolver de `configs/_shared`/per-órgão e de manifest
(`datasets.yaml`) usado por `cli/main.py` e `orchestration/run.py`, de modo que
`pyauditor measure` e `pyauditor run` sempre resolvam o mesmo diretório de config
e o mesmo manifest para o mesmo órgão/competência.

Hoje a precedência diverge: `main._resolve_manifest_path` prefere `_shared` primeiro,
enquanto `run._manifest_for` prefere per-órgão e só então `_shared` — o que pode levar
os dois comandos a usar delimiters/datasets diferentes para o mesmo órgão (ex.: MTur
usa `,` em 1.7/1.11/1.12 enquanto MinC usa `;`).

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [x] Existe um único resolver compartilhado para o diretório de config (`_shared` se is_dir, senão per-órgão) e para o manifest, com precedência única e documentada.
- [x] `cli/main.py` e `orchestration/run.py` usam o mesmo resolver — para o mesmo órgão+base, `measure` e `run` chegam ao mesmo config_dir e ao mesmo `DatasetManifest`.
- [x] `_resolve_shared_config_dir` em `orchestration/run.py` (definido e nunca chamado) é removido.
- [x] Divergência de precedência de manifest entre main e run eliminada e coberta por teste.

## Comments

- 2026-08-22 — Implementado. Novo módulo `src/pyauditor/config/resolution.py` com
  `resolve_config_dir`/`resolve_manifest_path`/`load_manifest_for` (precedência única:
  `_shared` vence, per-órgão fallback, alinhada ao ADR 0003). `cli/main.py` e
  `orchestration/run.py` agora usam o resolver compartilhado; removidas as funções locais
  (`_resolve_config_dir`, `_resolve_manifest_path`, `_resolve_shared_config_dir`, `_manifest_for`).
  Testes: `tests/test_config_resolution.py` (resolver unitário), convergência de precedência
  coberta por `test_cli_main_measure_resolves_shared_manifest_when_both_exist` e
  `test_execute_run_uses_shared_manifest_when_both_exist`. Suíte completa: 483 passed,
  90.33% coverage; mypy strict limpo.