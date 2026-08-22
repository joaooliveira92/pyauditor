# 03 — Análise SRP do pacote engine

Type: research
Status: resolved
Blocked by: —

## Question

Analisar o pacote `src/pyauditor/engine/` (pipeline.py 505, quality_gates.py 56, strategies/ — ratio 111, precomputed_table 97, segmented_ratio 77, external_catalog_sum 56, count_difference 46, base 44, _filters 44, _numbers 30, _target 23) com lente de SRP do spec: pipeline como orquestrador, strategies como estratégias de cálculo, separação shape/meta/dados. Incluir módulos de raiz vinculados `categoria_filter.py` (filtro por categoria, usado pelo pipeline) e `periodo.py` (período de aferição); avaliar a posição de `periodo.py` (mora na engine, mas é consumido por cli/interactive/rom). Evidências precisas por candidato, classificação CRÍTICA..NÃO RECOMENDADA, plano por arquivo.

Considerar testes correspondentes (`tests/test_engine_*.py`, `test_periodo.py`).

Deliverable: artefato `notes/pacote-engine.md` + **Answer** com principais candidatos.

## Answer

Resolvido em `.scratch/app-audit/notes/pacote-engine.md` (análise sem alterar código; validação: `mypy` strict OK em 15 arquivos, `pytest` 506 passed/86.54%, `ruff` conta erros pré-existentes do repo).

Candidatos por prioridade (SRP):

- **ALTA — `engine/pipeline.py`** (505 físicas / ~419 lógicas): agrega 5 responsabilidades (dataclasses de resultado, leitura de config+discovery, acesso a arquivo/CSV, validação de colunas, orquestração `measurement_source`/`measure`/versão). 6 motivos independentes de mudança; maiores cc: `discover_config_files` 14, `measurement_source` 11. API é pública e consumida fora do pacote; `cli/measure.py:47` importa o privado `_pipeline_version` e `cli/measure.py:488–519` remonta `MeasurementResult` manualmente. Plano: criar `engine/loading.py`, `engine/discovery.py` e `engine/version.py` (com `pipeline_version()` público) preservando a API por re-export.
- **MÉDIA**: `strategies/precomputed_table.py` (`calculate` 62 linhas/cc=22 — extrair `_row_result`/`_row_penalty`/`_headline`); duplicação transversal de leitores CSV (`pipeline.load_rows` vs `categoria_filter.read_raw_csv`).
- **BAIXA**: `periodo.py` (divisão interna só de mensagens/formatação), `ratio._aggregate` (3 agregações), `quality_gates._first_violation`, seam furada (`render.py` importa `strategies._target` direto; `as_float` fora do `__init__`), remontagem manual em `cli/measure.py`.
- **NÃO RECOMENDADA**: `segmented_ratio.py`, `count_difference.py`, `external_catalog_sum.py`, `base.py`, `_filters/_numbers/_target.py`.

Sobre `periodo.py` (fato verificado): o módulo está na **raiz** de `pyauditor/`, não dentro de `engine/`; é utilitário de domínio compartilhado por 6 subpacotes — **não mover para `engine/`** (inverteria a direção das dependências); a posição atual está correta, com apenas divisão interna opcional de mensagens/formatação.