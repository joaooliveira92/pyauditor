# 05 — Discovery determinístico + teste de não-regressão por competência

**What to build:** clone fresco sem `split` prévio mede identico a clone com derivados antigos. `discover_config_files`/`discover_configs` têm comportamento determinístico documentado e um teste de snapshots garante que os 14 indicadores × 2 órgãos × competência 06/2026 não regredem.

**Blocked by:** 02 — Single-source, 03 — Extrair acceptance_test, 04 — Split como filtro em memória

**Status:** done

- [x] `engine/pipeline.py:discover_config_files` documentado e testado: lê exclusivamente `configs/_shared/*.yaml` (não `configs/<orgao>/*.yaml`) quando `expected_orgao` é passado; `glob` não captura mais `datasets.yaml`/`categorias.yaml` nem derivados; typo `indicador:` falha com mensagem acionável
- [x] `config/manifest.py:load_manifest` passa a carregar `configs/_shared/datasets.yaml` por padrão, com fallback explícito para `configs/<orgao>/datasets.yaml` se existir (transição)
- [x] Teste de snapshot `tests/test_measure_snapshots_2026_06.py` (ou similar) roda `measure` para MinC e MTur sobre `tests/fixtures/` ou `input/` sintético e compara `summary.to_dict()` contra snapshots commitados — falha se qualquer `result_pct`/`penalty_points` mudar
- [x] CI verde: `uv run pytest`, `uv run mypy --strict`, `uv run ruff check` sem novos suppressions; `git ls-files | grep configs` lista só `_shared/` + `categorias.yaml` por órgão
