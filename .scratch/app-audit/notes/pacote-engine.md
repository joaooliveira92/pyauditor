# Análise SRP — pacote `engine` (+ módulos de raiz vinculados)

**Ticket:** `.scratch/app-audit/issues/03-pacote-engine.md`
**Escopo:** `src/pyauditor/engine/` (pipeline.py, quality_gates.py, strategies/*) + `categoria_filter.py` e `periodo.py`.
**Natureza:** análise/pesquisa. Nenhum arquivo de código foi modificado.

## 1. Resumo executivo

Foram analisados 14 arquivos (12 do pacote `engine` + 2 de raiz), total de 1680 linhas físicas.

| Prioridade | Candidatos |
|---|---|
| ALTA | `engine/pipeline.py` |
| MÉDIA | `strategies/precomputed_table.py` (método `calculate`, cc=22); duplicação de leitores CSV (`pipeline.load_rows` vs `categoria_filter.read_raw_csv`) |
| BAIXA | `periodo.py` (divisão interna; não mudar de pacote); `ratio._aggregate`; `quality_gates._first_violation`; `engine/__init__.py` vazio + seam furado; remontagem manual em `cli/measure.py` |
| NÃO RECOMENDADA | `segmented_ratio.py`, `count_difference.py`, `external_catalog_sum.py`, `base.py`, `_filters.py`, `_numbers.py`, `_target.py`, `strategies/__init__.py`, `quality_gates.py` |

Não há candidato CRÍTICA. O pacote já foi alinhado em refatorações recentes (ticket 02 — backbone `measurement_source()`; uma estratégia por shape; helpers puros isolados em `_filters`/`_numbers`/`_target`) e a fronteira de cada arquivo é razoavelmente clara. O maior retorno está em `pipeline.py` (agregador de várias responsabilidades) e no achado transversal dos leitores CSV duplicados.

### Ferramentas e limitações

- `ruff` 0.15.0, `mypy` 1.19.1 (strict) e `pytest` 9.0.2 disponíveis. `radon`/`xenon` **não estão instalados** (limitação registrada conforme `map.md`); a complexidade ciclomática (cc) foi calculada com script próprio sobre `ast` (contagem aproximada de If/For/While/Try/With/Assert + BoolOp + comprehension + ExceptHandler, base +1).
- `mypy` strict passou nos 15 arquivos do escopo: `Success: no issues found in 15 source files`.
- `pytest`: **506 passed, 34 skipped**, cobertura 86.54% (gate de 85% atingida). Suíte completa verde.
- `ruff` no escopo: 177 erros (a maioria E501 linha >80 caracteres, alguns S101 assert em produção e I001 de imports). Estado pré-existente do repositório (687 erros em `src/` inteiro). Fato observado, usado como evidência quantitativa, não é alvo deste ticket.
- Linhas "lógicas" são aproximadas: linhas não vazias e sem comentário de linha inteira (docstrings contam como linhas).

## 2. Posição física de `periodo.py` (fato verificado)

`periodo.py` está em `src/pyauditor/periodo.py`, na **raiz** do pacote, e não dentro de `engine/`. O enunciado do ticket ("mora na engine") é impreciso quanto à localização real.

Consumidores (levantados com `rg`): `engine/pipeline.py:23`, `cli/main.py:37`, `cli/measure.py:56`, `cli/report.py:27`, `cli/consolidate.py:28`, `cli/split.py:47`, `interactive/flow.py:43`, `orchestration/run.py:71`, `rom/render.py:20`, `excel/sintetico.py:86`, `excel/consolidate.py:51`, `excel/inms_1_1_audit.py:45`. A única dependência é a biblioteca padrão.

Avaliação de posição:

1. `periodo.py` **não deve ser movido para `engine/`**. Se fosse, `cli/`, `interactive/`, `orchestration/`, `rom/` e `excel/` passariam a depender de `engine` por um motivo que não é o motor de medição — inverteria a direção das dependências (as camadas altas já dependem de `engine` legitimamente; `periodo` não é um deles).
2. A posição atual (raiz de `pyauditor`) está **correta**: é um utilitário de domínio compartilhado sobre `competência`, usado por mais de 10 arquivos de 6 subpacotes. Esta conclusão é baseada nos fatos de consumo; confiança média (não medimos dependência futura).
3. Se um dia o repositório criar um subpacote de domínio compartilhado, `periodo.py` é candidato natural (junto com `categoria_filter.py`). Hoje não há nada a fazer.

O que vale fazer em `periodo.py` é apenas divisão interna (BAIXA). O arquivo (424 físicas / ~326 lógicas) acumula quatro grupos coesos sobre o mesmo tema:

1. Derivação da janela: `PeriodoAfericao` + `month_bounds` (109–148).
2. Filtro puro de linhas: `filter_periodo` (233–315; 83 linhas, cc=11), `_cell_interval` (187–230, cc=10), `PeriodFilterResult`.
3. Validação de config: `require_period_column` (151–184) + exceções `PeriodColumnMissingError`/`PeriodColumnNotFoundError`.
4. Formatação e mensagens: `format_date_br`, `format_period_br`, `empty_window_message`, `discard_message` (318–411).

Os grupos ficam juntos porque o tema é único ("competência/período") e mudanças em um costumam afetar os demais (novo formato de célula afeta o filtro e as mensagens) — o motivo de mudança não é independente entre eles. A única subdivisão com nome bom seria extrair as **mensagens/formatação** para `periodo_messages.py` (única área com motivo de mudança independente: o texto de relatório muda sem mexer na semântica do filtro), mas o retorno é baixo. **Confiança alta** — `test_periodo.py` (166 linhas) cobre bem as quatro áreas.

## 3. Ranking dos candidatos do pacote `engine`

### 3.1 `engine/pipeline.py` — ALTA

- **Linhas:** físicas 505 / lógicas ~419. 3 classes (dataclasses), 15 funções.
- **Símbolos públicos:** `MeasurementProvenance`, `SourceBundle`, `MeasurementResult`, `load_config`, `load_rows`, `resolve_source`, `discover_config_files`, `discover_configs`, `measurement_source`, `measure`; privados `_pipeline_version`, `_detect_delimiter`, `_inject_orgao`, `_validate_columns`, `_collect_config_columns`, `_ORGAO_CONTRACT`.

**Cinco responsabilidades distintas no mesmo arquivo:**

1. Modelos de resultado do domínio: `MeasurementProvenance` (34–48), `SourceBundle` (50–67), `MeasurementResult` (70–111, com `hard_failure` 81–87 e `systematic_failure` 89–111).
2. Leitura de config (YAML → model): `load_config` (186–206), `discover_config_files` (297–349; cc=14), `discover_configs` (352–359), `_inject_orgao` (286–294 com `_ORGAO_CONTRACT` 280–283). Inclui detecção de typos, hash do conteúdo e injeção de órgão.
3. Acesso a arquivos/CSV: `resolve_source` (249–277) + `_detect_delimiter` (222–246) + `load_rows` (209–219).
4. Validação de colunas: `_collect_config_columns` (135–173) + `_validate_columns` (176–183).
5. Orquestração: `measurement_source` (362–441; 80 linhas, cc=11), `measure` (444–505; 62 linhas), `_pipeline_version` (114–131; usa `importlib.metadata`/git/subprocess).

**Motivos independentes de mudança:** (a) novo formato de CSV/delimitador; (b) regras de descoberta de config (typos de chave, órgão); (c) validação de colunas; (d) origem unfilterable/período; (e) semântica de quality gate + hard/systematic; (f) origem/versão do pipeline. São seis motivos independentes para ~500 linhas.

**Sinais quantitativos (maiores cc por função):**

| Função | cc | Linhas |
|---|---|---|
| `discover_config_files` | 14 | 53 |
| `measurement_source` | 11 | 80 |
| `_detect_delimiter` | 9 | 25 |
| `_collect_config_columns` | 7 | 39 |
| `load_config` | 7 | 21 |

Acima do limiar de 40 linhas ficaram `discover_config_files`, `measurement_source` e `measure`.

**Evidências qualitativas:**

- O arquivo mistura infra de arquivo/catálogo (`resolve_source`, `discover_*`, `_detect_delimiter`) com regra de negócio/orquestração e modelos de resultado. O padrão de `_collect_config_columns` faz `getattr(calc, attr, None)` sobre 16 atributos de shapes concretas (149–172) — um conhecimento de shapes dentro do pipeline que poderia viver em cada estratégia.
- **API privada atravessada por módulo externo:** `cli/measure.py:47` importa `_pipeline_version` (símbolo privado). Mais: `cli/measure.py:488–519` **reconstrói `MeasurementResult`/`MeasurementProvenance` na mão** (QualityGateRunner + SHAPE_REGISTRY + hashes + dataclass), porque `measure()` não serve para config derivada (per-categoria). Isso é evidência de que o pipeline deveria expor um helper de composição para configs derivadas.
- Sem ciclo de import hoje: `pipeline` depende apenas de `config.*`, `categoria_filter`, `engine.strategies`, `quality_gates`, `logging` e `periodo` (levando para baixo). A divisão não deve criar ciclo.

**Dependências relevantes:** `categoria_filter.read_raw_csv` (:16), `config.manifest`, `config.models`, `engine.quality_gates`, `engine.strategies.SHAPE_REGISTRY`, `logging`, `periodo`.

**Risco/benefício:** a API é pública e consumida por `cli/measure.py:44–51`, `cli/split.py:44`, `excel/sintetico.py:77`, `rom/render.py:16–19`, `rom/summary.py:9–10`, `cli/report.py:21`, `orchestration` e vários testes. A divisão precisa preservar os imports (re-export). **Risco** médio; **benefício** alto (arquivo cai para ~250 linhas e cada responsabilidade ganha casa testável).

**Plano por arquivo (ordem segura — preserva API por re-export):**

1. Testes antes: garantir a suíte completa verde (hoje: 506 passando).
2. Criar `pyauditor/engine/loading.py`: mover `_DELIMITER_CANDIDATES`, `_detect_delimiter`, `resolve_source`, `load_rows`.
3. Criar `pyauditor/engine/discovery.py`: mover `_ORGAO_CONTRACT`, `_inject_orgao`, `load_config`, `discover_config_files`, `discover_configs`.
4. Criar `pyauditor/engine/version.py`: mover `_pipeline_version` para `pipeline_version()` (público), rompendo a dependência do `_` privado em `cli/measure.py:47`.
5. Em `pipeline.py` ficam `measurement_source`, `measure`, `_collect_config_columns`, `_validate_columns` e as três dataclasses, **re-exportando** os símbolos movidos (ex.: `load_config` vem de `engine.discovery`).
6. Avaliar (sem engenharia especulativa) um helper `measure_derived(config, rows, ...)` para o caminho categórico que hoje é remontado em `cli/measure.py:488–519`.
7. Testes depois: mesma suíte, nenhuma mudança de assinatura pública; reforçar `test_pipeline_load_rows` (hoje só cobre CSV simples e headerless).

**Confiança:** alta (fatos objetivos e consumidores mapeados por `rg`).

### 3.2 `strategies/precomputed_table.py` — MÉDIA

- `PrecomputedTableStrategy.calculate` (33–94): **62 linhas, cc=22** — maior cc do pacote.
- Motivos internos de mudança no mesmo método: (a) regra de linha vazia/parse; (b) penalidade em **três ramos** — `penalty_column` presente (57–60) | recalculada de `result_is_percent` + `shortfall` (61–64) | flat `max(value-target,0)` (65–66); (c) acumulador ponderado `numerator_column`/`denominator_column` (72–80); (d) headline em três vias: ponderada/média/`0.0` (82–87).
- **Plano:** extrair helpers privados do mesmo arquivo — `_row_result(...)`, `_row_penalty(...)`, `_headline(...)` — sem mudar a API. Manter a suíte `test_precomputed_table.py` e o teste de ingestão manual (`test_manual_ingestion_inms_1_8.py`). Se passar de ~150 linhas, criar pasta `strategies/precomputed/`.
- **Benefício** médio (legibilidade), **risco** baixo, **confiança** alta.

### 3.3 Duplicação de leitores CSV — MÉDIA (transversal)

- **Fato:** existem **dois** leitores de `csv.DictReader` com lógica próxima:
  1. `engine/pipeline.py` — `load_rows` (209–219);
  2. `categoria_filter.py` — `read_raw_csv` (58–78), que além do `strip` faz a **normalização de header** `"Grupo executor"` → `"Grupo_executor"` (47–55).
- `measurement_source` usa `read_raw_csv` **de propósito** (pipeline.py:389–394), e `load_rows` é usado por `cli/split.py`. Dois leitores com comportamento convergente em módulos separados viram risco de drift (o mesmo tipo de problema que o ticket 02 resolveu para `measure()` ao criar a backbone).
- **Plano (hipótese):** unificar em um só carregador no `engine/loading.py` (item 3.1) com dois modos ("header normalizado" vs "header bruto"), com `load_rows` virando wrapper. **Antes:** teste de normalização de alias e de linhas ragged no `test_pipeline_load_rows` (as linhas ragged são citadas no comentário do código — sem teste hoje). **Depois:** `test_measure`, `test_measurement_source`, `test_cli_split`.
- **Risco:** médio (é o ponto quente de produção; não pode mudar comportamento observável). **Confiança:** média.

### 3.4 `categoria_filter.py` — BAIXA

- 132 linhas físicas, 4 funções. Módulo coeso (filtragem categoria/`Grupo_executor`), mas com **duas responsabilidades mescladas**: (a) leitura raw de CSV com normalização de header (`read_raw_csv`, 58–78) — a mesma da seção 3.3; (b) resolução de categorias + validação de `outros` — `compute_categoria_values` (81–132; 52 linhas, cc=12) combina em um laço a resolução (`in_values`/`catch_all_contains`) com duas validações de sobreposição (93–104 e 121–127).
- **Plano:** extrair `_validate_in_values_disjoint(...)` e `_validate_post_resolution(...)` privadas. Manter as exportações públicas (`compute_categoria_values`, `GRUPO_EXECUTOR_COLUMN`, `base_config_stem`, `read_raw_csv`), pois são usadas por `cli/split.py:35`, `excel/sintetico.py:64`, `excel/inms_1_1_audit.py:39` e por `engine`. **Confiança:** média.

### 3.5 `strategies/ratio.py` — BAIXA

- `_aggregate` (71–99): cc=8, dispatch em **três modos** — `count_distinct` (72–75) | `sum` (77–91, com ramo `extra` vs `subtract`) | `precomputed` (93–99, com assert de linha única). Um único método decide três comportamentos.
- **Plano:** extrair `_aggregate_count_distinct`, `_aggregate_sum`, `_aggregate_precomputed` (ficam na `ratio.py` em até ~150 linhas; depois vão para `strategies/ratio/_aggregations.py`). A suíte `test_remaining_ratio_indicators.py` (cobre sum/subtract/extra/precomputed) e `test_ratio_tracer_bullet` (acceptance) protegem.
- **Confiança:** alta (mudança estrutural mínima).

### 3.6 `quality_gates.py` / `engine/__init__.py` / seam de `strategies` — BAIXA (observações)

- `quality_gates.py` (56 linhas): bem separado (`RejectedRow`, `QualityGateReport`, `QualityGateRunner`). Ponto de observação: `_first_violation` (45–55) faz dispatch por `isinstance`, que tende a crescer a cada novo tipo de `QualityGateCheck` (hoje dois tipos — fato). **Antes** de tocar no gate, adicionar um teste para o caminho de erro de `id_column` ausente (`:36–44`), que não está coberto atualmente (o teste tem 23 linhas). Não mover o arquivo.
- `engine/__init__.py` é **vazio** (0 linhas). A API pública hoje é via submódulos. Porém um consumidor fura a seam: `rom/render.py:18` importa `shortfall` de `engine.strategies._target` — e a seam declarada em `strategies/__init__.py` (re-export `filter_rows`, `parse_decimal`, `meets_target`, `safe_pct`, `shortfall`) está **sem `as_float`**. Recomendação (hipótese): rotear `render.py` pela seam e adicionar `as_float` à re-exportação. Decidir entre fachada em `engine/__init__.py` ou deixar vazio (ambos defensíveis). Risco baixo.
- `cli/measure.py:488–519` remonta o resultado manualmente (ver 3.1 passo 6).

### 3.7 NÃO RECOMENDADA (arquivos pequenos e coesos)

| Arquivo | Linhas | Motivo |
|---|---|---|
| `strategies/base.py` | 44 | Contrato/Protocol + tipo `CalculationResult`; só uma responsabilidade. |
| `strategies/segmented_ratio.py` | 77 | Estratégia única; teste dedicado 126 linhas. |
| `strategies/external_catalog_sum.py` | 56 | Única responsabilidade (soma Anexo E); cc 5; teste 147 linhas. |
| `strategies/count_difference.py` | 46 | Fórmula CNI; teste 137 linhas. |
| `strategies/_numbers.py`, `_target.py`, `_filters.py` | 30/23/44 | Helpers já extraídos e coesos; mais divisão reduziria clareza. |
| `strategies/__init__.py` | 35 | Registro + seam. Único ponto: `as_float` fora de `__all__`. |
| `quality_gates.py` | 56 | Dataclasses + runner pequenos e bem separados. |

Fragmentar esses arquivos é divisão artificial por linhas — contra a regra do spec.

## 4. Dimensão testes (referência por arquivo)

- `test_periodo.py` (166): quatro classes cobrem janela, filtro, coluna obrigatória e mensagens; casos com dias-limite, strict/default, idempotência e não-mutação. Boa fundação para o split interno.
- `test_measurement_source.py` (144): backbone (resolução → gates → filtro período → supressão de logs).
- Acceptance por shape: `test_ratio_tracer_bullet.py` (54), `test_remaining_ratio_indicators.py` (234 inclui sum/subtract/extra/precomputed), `test_segmented_ratio.py` (126), `test_precomputed_table.py` (144), `test_count_difference.py` (120), `test_external_catalog_sum.py` (129). Todos com `matches acceptance test` + caso unitário.
- `test_strategy_pooling.py` (66): contrato `pool_numerator_denominator` dos cinco shapes via `SHAPE_REGISTRY` (loop) e casos malformados — bom "guard-rail" para mudar `base`.
- `test_numbers.py` (30): unitário de `_numbers`.
- `test_pipeline_load_rows.py` (22): fraco — não cobre `_detect_delimiter`, normalização do header, linhas ragged nem divergência de delimitador. **Gap conhecido** antes de tocar na leitura.
- `test_measure.py` (testa `cli.measure`, 212): hard-failure, erros de I/O, equipe — funciona como teste de API externa do engine.
- `test_multi_asset_discovery.py` (101): `discover_configs`/`measure` para múltiplos ativos.
- Gaps menores: sem teste unitário direto de `_target`/`_filters` (cobertos indiretamente pelos testes de shape; o `DurationAtMost` aparece apenas como fixture de config, ver `test_config_per_orgao.py:37`).

## 5. Plano incremental (pacote)

1. **Fortalecer testes (risco zero):** `test_pipeline_load_rows` (delimiter + header alias + ragged) e `test_quality_gates` (caminho de erro de `id_column`).
2. **Extrações sem mudança de comportamento:** `ratio._aggregate_*`, helpers de `precomputed_table`, validadores de `categoria_filter`, formatadores de `periodo_messages`. Cada extração com a suíte verde antes/depois.
3. **Split de `engine/pipeline.py`:** criar `loading.py`, `discovery.py`, `version.py` com re-export preservando a API.
4. **Consolidar os leitores CSV** numa única origem (uma vez que o item 3 estiver feito; só se houver teste suficiente).
5. **Fechar a seam de `strategies`:** re-exportar `as_float` e redirecionar `render.py` pela seam; decidir fachada vs vazio em `engine/__init__.py`.
6. **`cli/measure.py`:** usar helper da engine para a derivação categórica, quando existente.

Validação por etapa: `ruff check <módulo>`; `mypy src tests`; `pytest -q` (gate de cobertura 85%); conferir que os "matches acceptance test" continuam passando sem alteração de comportamento.

## 6. Fato observado versus hipótese (resumo)

- **Fatos:** localização física de `periodo.py` (raiz; o enunciado do ticket "mora na engine" é impreciso); 506 testes / 86.54% verdes; cc e linhas por função via `ast`; imports privados atravessados (`_pipeline_version` em `cli/measure.py:47`; `_target` em `rom/render.py:18`); duplicação de leitores CSV; `engine/__init__.py` vazio; `compute_categoria_values` cc=12; `PrecomputedTableStrategy.calculate` com 62 linhas e cc=22; lista de consumidores por símbolo.

- **Hipóteses:** ganho real do split de `pipeline.py` em módulos (não medido); impacto de unificar os leitores CSV; mérito da fachada em `engine/__init__.py`; ordenação da prioridade (não quantificada em valor, baseada em sinais quantitativos e qualitativos).