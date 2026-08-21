# 01 — Higienização e prefatoração: desentrack de derivados + teste de invariantes compartilhados

**What to build:** o repo fica em estado higiênico e com rede de segurança para a migração: derivados `configs/*/inms-*.*.yaml` deixam de ser trackeados (respeitando o `.gitignore` já existente), e um teste novo garante que invariantes contratuais compartilhados entre MinC e MTur não divergem silenciosamente.

**Blocked by:** None — can start immediately

**Status:** done

- [x] `git rm --cached configs/*/inms-*.*.yaml` executado; `git status` não lista mais derivados como tracked; `.gitignore` `configs/*/inms-*.*.yaml` continua cobrindo
- [x] Teste `tests/test_configs_shared_invariants.py` (ou similar) compara `calculation`/`target`/`penalty`/`quality_gates` entre MinC e MTur para cada `inms-NN` e falha se divergirem (exceto allowlist explícita: `scope`, `acceptance_test`, comentários)
- [x] `uv run pytest -k test_configs_shared_invariants` verde; `uv run mypy --strict` e `uv run ruff check` verdes sem novos ignores
- [x] Nenhum `measure`/`report` existente quebrado — `discover_config_files` ainda encontra os mesmos configs antes da migração
