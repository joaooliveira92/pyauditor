# 02 — Análise SRP do pacote config

Type: research
Status: resolved
Blocked by: —

## Question

Analisar o pacote `src/pyauditor/config/` (models.py 372, catalog.py 113, resolution.py 114, manifest.py 106, categorias.py 104, niveis.py 24, _paths.py 16) com lente de SRP do spec: single-responsibility, models como contêiner de regras, catálogos/loaders, resolução de dupla fonte. Analisar também `src/pyauditor/config/catalogs/anexo_e.yaml` (dados, não lógica — não é candidato por si só). Evidências precisas para cada candidato e fato vs. hipótese, classificação CRÍTICA..NÃO RECOMENDADA, plano por arquivo.

Considerar testes de config (ex.: `tests/test_catalog.py`, `test_manifest.py`, `test_models.py`, `test_categorias.py`, `test_config_per_orgao.py`, `test_config_resolution.py`).

Deliverable: artefato `notes/pacote-config.md` + **Answer** com o candidato-chave na resolução.

## Answer

Pacote `config` com pouco risco de SRP. Único candidato real: **`models.py`
(MÉDIA, 372 físicas/206 lógicas, 96% coberta)** — 28 modelos Pydantic em 5
grupos contíguos com motivos independentes de mudança; a separação concreta é
o bloco **acceptance test** (`models.py:266-342`, 9 símbolos) que **só os
testes consomem** (produção apenas o anula: `cli/split.py:129`,
`cli/measure.py:484`): extrair para `config/acceptance.py` com reexport em
`models.py` (API preservada, risco nulo, sem ciclo de import). Os 3 validators
(cc máx. 9) contêm as regras de negócio no modelo certo — positivo, não
violação. Demais arquivos: `catalog.py`, `manifest.py`, `categorias.py`,
`resolution.py`, `niveis.py`, `_paths.py` → **NÃO RECOMENDADA** (loader/1
responsabilidade, pequenos, coesos, 100% cobertos exceto ramos de erro I/O em
`catalog.py` 85% e `_paths.py` 83%); `catalogs/anexo_e.yaml` é dado, não
candidato. `mypy` strict limpo; 53 testes das suítes de config passando.

Nota completa: `notes/pacote-config.md` (evidências arquivo:linha, plano por
arquivo e validações).