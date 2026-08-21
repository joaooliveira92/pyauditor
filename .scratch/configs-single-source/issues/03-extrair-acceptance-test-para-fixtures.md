# 03 — Extrair `acceptance_test` dos YAMLs de produção para fixtures de teste

**What to build:** números de aceitação por competência deixam de poluir configs de produção. Cada `acceptance_test` hoje embutido em `inms-NN.yaml` (snapshot de 06/2026) migra para `tests/acceptance/<orgao>/<competencia>.yaml` (ou `tests/fixtures/acceptance/`), e o teste parametrizado passa a ler de lá.

**Blocked by:** 02 — Single-source: `configs/_shared/` + loader com injeção de órgão

**Status:** done

- [x] `IndicatorConfig.acceptance_test` torna-se opcional no base `_shared/` (já é `| None`) e é removido dos 14 YAMLs canônicos; 28 blocos `acceptance_test:` deletados de produção
- [x] Fixtures criadas em `tests/acceptance/MinC/2026-06.yaml` e `tests/acceptance/MTur/2026-06.yaml` (ou equivalente) com os mesmos `expected` removidos, preservando `shape`/`numerator`/`denominator`/`result_pct`/`penalty_points`
- [x] Teste parametrizado de smoke (`tests/test_acceptance_smoke.py` ou similar) atualizado para carregar `IndicatorConfig` de `_shared/` + `expected` da fixture e comparar `measure()` vs fixture — `uv run pytest -k acceptance` verde
- [x] Nenhum YAML em `configs/_shared/` contém `acceptance_test:` após a migração (`grep -r acceptance_test configs/_shared` vazio)
