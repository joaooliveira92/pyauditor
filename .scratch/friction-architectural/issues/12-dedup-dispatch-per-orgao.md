# 12 — Dedup do dispatch per-órgão `main`/`run`

**What to build:** a expansão "para cada órgão: computa config_dir/data_dir/output_dir/
manifest, então chama `run_*`" passa a existir uma única vez, compartilhada por
`cli/main.py` e `orchestration/run.py`.

Hoje ela é feita duas vezes com sémântica própria: `main` usa
`_resolve_config_dir`+`_resolve_manifest_path`, `run` usa `_manifest_for` +
`materialize=False`. Após este ticket:

- os wrappers idênticos `_capa_path_for` (em `main.py` e `run.py`, ambos delegando a
  `capa_paths.py`) viram um só;
- a divergência `materialize=True` (main) vs `materialize=False` (orchestration) é
  reconciliada de forma explícita e testada (o caminho `materialize=False` do split só é
  exercitado via `run` hoje);
- a "defense-in-depth" que executa `check_report_ready`/`check_consolidate_ready` duas
  vezes por comando é reduzida a uma.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] Um único dispatch per-órgão usado por `main` e `run` (config_dir/data_dir/output_dir/manifest derivados igualmente).
- [ ] `_capa_path_for` duplicado removido (um só wrapper).
- [ ] `materialize=True`/`False` reconciliado e coberto por teste — ambos os caminhos do split exercitados.
- [ ] Defense-in-depth de `check_report_ready`/`check_consolidate_ready` executada uma vez por comando.
- [ ] Suíte completa verde.