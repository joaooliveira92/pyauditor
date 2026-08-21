# 02 — Single-source: `configs/_shared/` + loader com injeção de órgão

**What to build:** os 14 indicadores têm uma única fonte da verdade. `configs/_shared/inms-01.yaml`…`inms-14.yaml` + `configs/_shared/datasets.yaml` são os canônicos (sem `scope.orgao` obrigatório, sem `acceptance_test`); `configs/MinC/categorias.yaml` e `configs/MTur/categorias.yaml` permanecem como único arquivo por órgão. `measure`/`report` passam a carregar de `_shared/` e injetar `scope.orgao`/`contract` em runtime via `--orgao`.

**Blocked by:** 01 — Higienização e prefatoração

**Status:** done

- [x] `configs/_shared/` criado com 14 YAMLs base (copiados de MinC, sem `scope.orgao`/`contract`/`acceptance_test` hard-coded) + `datasets.yaml` único; `models.Scope.orgao` aceita `None` no base ou é injetado pelo loader
- [x] `engine/pipeline.py:discover_config_files` e `discover_configs` atualizados para ler `configs/_shared/*.yaml` quando `expected_orgao` é informado, injetando `scope.orgao` e `scope.contract` (ex.: `"40/2022 - Ministério da Cultura"` vs `"...Turismo"`) sem mutar o arquivo em disco
- [x] `configs/MinC/inms-*.yaml` e `configs/MTur/inms-*.yaml` removidos (ou mantidos como shim de compatibilidade que delega para `_shared/` com warning) — `git diff --stat` mostra -28 arquivos base duplicados
- [x] `uv run pyauditor measure 2026-06 --orgao MinC` e `--orgao MTur` produzem os mesmos ROMs que antes (comparação de `summary.json` byte-identica para competência 06/2026)
- [x] `mypy --strict` verde; testes existentes ajustados para novo `discover_config_files` sem `type: ignore`
