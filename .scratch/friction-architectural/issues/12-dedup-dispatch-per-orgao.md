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

**Status:** done

- [x] Um único dispatch per-órgão usado por `main` e `run` (config_dir/data_dir/output_dir/manifest derivados igualmente).
- [x] `_capa_path_for` duplicado removido (um só wrapper).
- [x] `materialize=True`/`False` reconciliado e coberto por teste — ambos os caminhos do split exercitados.
- [x] Defense-in-depth de `check_report_ready`/`check_consolidate_ready` executada uma vez por comando.
- [x] Suíte completa verde.

## Comments

- 2026-08-22 — Implementado. (a) Novo `per_orgao_paths()` em
  `config/resolution.py` (`PerOrgaoPaths`) — expansão per-órgão única
  (config_dir ADR 3 + data/output/report `/<orgao>` + manifest) usada por
  `cli/main.py` (measure/split/report) e `orchestration/run.py` (split/
  measure/report) em vez de cada entry point reimplementar a derivação.
  (b) `_capa_path_for` de `cli/main.py` removido — todos usam
  `capa_paths.resolve_capa_path` diretamente. (c) `materialize` explícito:
  `main` passa `True` (CLI standalone grava artefatos), `orchestration`
  `False` (in-memory), e novo teste `test_run_split_materialize_false_computa_sem_gravar_artefatos`
  em `test_cli_split.py` exercita o caminho outrora só exercido via `run`.
  (d) Pre-flight duplicado de `check_report_ready`/`check_consolidate_ready`
  removido de `cli/main.py` — `run_report`/`run_consolidate` são o defense-in-
  depth único por comando. Suíte completa: 499 passed, 86.33% coverage;
  mypy strict e ruff limpos.