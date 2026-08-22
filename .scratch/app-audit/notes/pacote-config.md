# Nota SRP — pacote `config` (ticket 02)

Data: 2026-08-22 · Escopo: `src/pyauditor/config/` (`models.py` 372,
`catalog.py` 113, `resolution.py` 114, `manifest.py` 106, `categorias.py` 104,
`niveis.py` 24, `_paths.py` 16) + recurso `catalogs/anexo_e.yaml` (688 linhas,
dado, dado como não candidato).

## Métricas e limitações

- Ferramentas executadas: `ruff` (lint + format check), `mypy` (strict),
  `pytest` + cobertura.
  **Limitação registrada:** `radon`/`xenon` não estão instalados — a
  complexidade ciclomática abaixo foi obtida por análise própria da AST
  (método McCabe simplificado: `If`/`For`/`While`/`ExceptHandler`/`Assert`/
  `IfExp` + operandos de `BoolOp`). Valor aproximado, servindo de sinal, não
  de métrica de ferramenta.
- `mypy` strict: limpo — `Success: no issues found in 8 source files`.
- `ruff`: 26× `E501` (linhas > 80, pré-existentes) + 4× `I001` (imports não
  ordenados, auto-corrigíveis) + `ruff format --check` sinaliza 7 dos 8
  arquivos. Todo estilo pré-existente — **não usado como evidência de SRP**.
- `pytest`: **53 testes** das suítes do pacote passando
  (`test_catalog`, `test_manifest`, `test_models`, `test_categorias`,
  `test_config_per_orgao`, `test_config_resolution`,
  `test_configs_shared_invariants`). A suíte global segue verde (506, map.md).
- Cobertura (suítes do pacote + consumidores, `--cov-report=term-missing`):
  - `models.py` **96%** (207 stmts; 4 faltando: 97, 189, 362, 369);
  - `catalog.py` **85%** (62 stmts; 9 faltando: 56, 68-71, 79-80, 107-108 —
    ramos de `OSError`/`YAMLError`/`ValidationError`);
  - `manifest.py`, `categorias.py`, `resolution.py`, `niveis.py`: **100%**
    (não listados por `term-missing` = cobertura completa);
  - `_paths.py` **83%** (8 stmts; 1 faltando: 15).
- Linhas **físicas** = `wc -l`; linhas **lógicas** ≈ contagem de nós
  `ast.stmt`.

## Resumo dos candidatos

| Arquivo | Prioridade | Linhas físicas/lógicas | Cobertura | Confiança |
|---|---|---|---|---|
| `config/models.py` | **MÉDIA** | 372 / 206 | 96% | média |
| `config/catalog.py` | NÃO RECOMENDADA | 113 / 61 | 85% | alta |
| `config/resolution.py` | NÃO RECOMENDADA | 114 / 34 | 100% | alta |
| `config/manifest.py` | NÃO RECOMENDADA | 106 / 52 | 100% | alta |
| `config/categorias.py` | NÃO RECOMENDADA | 104 / 45 | 100% | alta |
| `config/niveis.py` | NÃO RECOMENDADA | 24 / 6 | 100% | alta |
| `config/_paths.py` | NÃO RECOMENDADA | 16 / 9 | 83% | alta |
| `config/catalogs/anexo_e.yaml` | NÃO CANDIDATO (dado) | 688 | — | alta |

---

## 1. `config/models.py` — **MÉDIA**

### Fatos observados

- **372 linhas físicas / 206 lógicas** — cruza o limiar de "observar" (300),
  mas fica abaixo de "candidato relevante" (500).
- **28 classes** (todas Pydantic, `frozen`/`strict`/`extra="forbid"` via
  `_StrictFrozen`, `models.py:46-51`) + **3 funções** (todas
  `@model_validator(mode="after")`) + 2 `type` aliases (`QualityGateCheck`
  `models.py:114`, `Filter` `models.py:156`, `Calculation` `models.py:243`,
  `AcceptanceTestExpected` `models.py:330`).
- **5 grupos de responsabilidade contíguos**, com motivos independentes de
  mudança distintos:
  1. **Envelope do config**: `Indicator` `models.py:54-63`, `Scope`
     `models.py:66-73`, `Source` `models.py:76-98` (com
     `_check_csv_or_dataset` `models.py:92-98`, cc≈2);
  2. **Quality gates**: `NotNullCheck` `models.py:101-105`, `InSetCheck`
     `models.py:107-111`, `QualityGates` `models.py:117-119`;
  3. **Filters**: `ColumnEquals` `models.py:122-125`, `ColumnNotEquals`
     `models.py:128-131`, `ColumnContains` `models.py:134-137`, `ColumnIn`
     `models.py:140-143`, `DurationAtMost` `models.py:146-152`;
  4. **Calculations** (núcleo do domínio): `RatioCalculation`
     `models.py:159-190` (com `_check_fields_for_aggregation`
     `models.py:174-190`, **cc≈8** — maior do módulo junto do de baixo),
     `SegmentedCategory` `models.py:193-198`, `SegmentedRatioCalculation`
     `models.py:201-205`, `CountDifferenceCalculation` `models.py:208-213`,
     `ExternalCatalogSumCalculation` `models.py:216-221`,
     `PrecomputedTableCalculation` `models.py:224-240`;
  5. **Acceptance test** (snapshot esperado de resultado): 9 símbolos
     `models.py:266-342` — `AcceptanceTestCategoryExpected` `266-272`,
     `AcceptanceTestOccurrenceExpected` `275-279`,
     `RatioAcceptanceExpected` `282-289`, `SegmentedRatioAcceptanceExpected`
     `292-298`, `CountDifferenceAcceptanceExpected` `301-309`,
     `ExternalCatalogSumAcceptanceExpected` `312-319`,
     `PrecomputedTableAcceptanceExpected` `322-327`,
     `AcceptanceTestExpected` `330-337`, `AcceptanceTest` `340-342`.
  - Envolvendo tudo: `Target` `models.py:253-256`, `Penalty` `models.py:259-263`
    (envelope), e a raiz `IndicatorConfig` `models.py:345-372` com
    `_check_target_for_shape` `models.py:356-372` (**cc≈9**).
- **Regras de negócio contidas nos models** (positivo, não violação): os 3
  validators vivem no modelo correto e são os únicos pontos de complexidade —
  `_check_fields_for_aggregation` (cc 8, `models.py:175`) e
  `_check_target_for_shape` (cc 9, `models.py:357`). Nenhuma função com mais
  de 40 linhas; nenhuma classe com métodos múltiplos.

### Motivos independentes para mudança

1. novo shape de `calculation` (ex.: indicador novo) → classe nova + `Calculation`
   `models.py:243` + `_check_target_for_shape` `models.py:357`;
2. novo tipo de `Filter` → `models.py:156`;
3. novo check de quality gate → `models.py:114`;
4. **alterar o formato do snapshot de acceptance test** (novos campos/ramos
   esperados, divergência contratual por competência) → bloco `models.py:266-342`
   **e nada mais**;
5. mudança no envelope (indicador/escopo/fonte/meta/penalidade).

### A separação concreta que vale a pena: bloco acceptance test

- Fato: **produção não consome os valores esperados**. O único uso em produção
  de `acceptance_test` é a própria declaração `models.py:354`; `cli/split.py:129`
  e `cli/measure.py:484` apenas o **anulam** (`"acceptance_test": None`). O
  consumo real do snapshot está **só nos testes**: `test_full_acceptance_smoke.py:38-41`,
  `test_remaining_ratio_indicators.py:41-42`, `test_precomputed_table.py:22-23`,
  `test_external_catalog_sum.py:38-39`, `test_count_difference.py:26-27`,
  `test_ratio_tracer_bullet.py:27-28`, `test_segmented_ratio.py:25-26` —
  todos lendo `config.acceptance_test.expected`.
- Fato: o bloco é **contíguo** (`models.py:266-342`), **sem dependências
  internas** (só importa `pydantic`), e os 10 símbolos correspondentes são
  reexportados no `__all__` `models.py:18-41`.
- Hipótese (declarada): o snapshot de aceitação é um **contrato de suporte a
  teste** (os fixtures `inms-*.yaml` carregam o esperado para a suíte
  comparar com a medição), não parte do schema de entrada do pipeline — por
  isso é o eixo com maior motivo independente de mudança (item 4 acima) e o
  único cuja extração reduz acoplamento real sem fragmentar o domínio.

### Plano sugerido

1. **Antes**: cobrir os 4 ramos descobertos de `models.py` (97 — `Source` com
   `dataset`+`csv`; 189 — `precomputed` sem coluna; 362 — shape não-externo
   sem `target`; 369 — `precomputed_table` percent sem penalty) em
   `tests/test_models.py`; a extração é mecânica e o comportamento não muda.
2. **Extrair**: novo módulo `src/pyauditor/config/acceptance.py` com os 9
   símbolos `models.py:266-342` movidos verbatim + seu próprio `__all__`.
   `IndicatorConfig.acceptance_test` (`models.py:354`) passa a importar
   `AcceptanceTest` de `acceptance.py`.
3. **API preservada**: manter em `models.py` a reexportação
   `from pyauditor.config.acceptance import ...` e `__all__` intacto — os 7
   arquivos de teste e o `engine` não mudam nenhum import. (Alternativa,
   sem reexport: atualizar os imports de `tests/test_full_acceptance_smoke.py:12-19`
   e demais — pior, não recomendada.)
4. **Depois**: rodar as 7 suítes de acceptance + suíte completa de config;
   `mypy` e `ruff` no pacote.
5. **Ordem segura**: 1 → 2 → 3 → 4. Risco de ciclo de importação: **nulo**
   (`acceptance.py` não importa nada do pacote).
6. **Risco/benefício**: risco baixo (mover verbatim, sem mudar comportamento);
   benefício moderado — o eixo de mudança nº 4 deixa de tocar o schema de
   entrada, e `models.py` volta para ~290 linhas físicas.

### Por que o restante NÃO deve ser dividido

- `Filter` (`models.py:122-156`) é usado por `Calculation`, gates e
  categorias; `Calculation` (`models.py:159-250`) é o coração do domínio e
  dependido por todas as estratégias (`engine/strategies/*` importam os
  shapes diretamente). Fragmentar em `filters.py`/`calculations.py` criaria
  dependências entre submódulos do próprio pacote e reexportações em cadeia
  para **zero ganho de isolamento**: os motivos de mudança 1-3 e 5 co-evoluem
  com o schema. Cobertura 96% e validators contidos confirmam que o módulo é
  coeso. É um "arquivo grande, mas relativamente coeso" → **MÉDIA**, não ALTA;
  só escalaria para ALTA se o schema continuar crescendo em shapes novos.

---

## 2. `config/catalog.py` — **NÃO RECOMENDADA**

### Fatos observados

- 113 físicas / 61 lógicas. 1 classe Pydantic (`CatalogItem` `catalog.py:24-38`),
  2 `TypedDict` (`_RawItem` `42-47`, `_RawCatalog` `50-51`), 1 `TypeGuard`
  (`_is_raw_catalog` `54-58`), 1 função de I/O de recurso empacotado
  (`_read_catalog_text` `61-71`, `importlib.resources` com fallback `as_file`),
  1 parse+shape (`_load_raw` `74-83`), 1 loader validado+cacheado
  (`load_anexo_e_catalog` `86-113`, `@lru_cache`, `MappingProxyType`).

### Análise SRP

- Duas razões de mudança (forma do catálogo vs. mecanismo de carga) — mas
  co-evoluem: alterar o shape do item muda modelo + `TypedDict` + validação
  juntos. É um **loader de catálogo**, padrão idêntico a `manifest.py` e
  `categorias.py`. Dividir (modelo vs. loader) fragmentaria um módulo de 113
  linhas bem testado (85%, falhas só nos ramos de erro I/O/YAML) e quebraria
  a simetria do pacote. Risco >> benefício.
- Consumidor único relevante: `engine/strategies/external_catalog_sum.py:11`
  (e testes `test_catalog.py`, `test_external_catalog_sum.py:12`).

---

## 3. `config/resolution.py` — **NÃO RECOMENDADA**

### Fatos observados

- 114 físicas / 34 lógicas. 4 funções puras (`resolve_config_dir` `39-48`,
  `resolve_manifest_path` `51-57`, `load_manifest_for` `60-70`,
  `per_orgao_paths` `91-114`) + 1 dataclass imutável `PerOrgaoPaths` `73-88`.

### Análise SRP

- Responsabilidade **única e bem nomeada**: resolução canônica de diretórios
  de config + expansão per-órgão (ADR 0003 `_shared` vs. per-órgão, a "dupla
  fonte" do ticket) e carga do manifest associado. Nenhum sinal de SRP —
  é o módulo que *resolve* a duplicação entre `cli/main.py:33` e
  `orchestration/run.py:57`. Acoplamento a `manifest.py:25` é de domínio, não
  de camada. Cobertura 100% (inclusive o contrato de precedência em
  `test_config_resolution.py`). Não dividir.

---

## 4. `config/manifest.py` — **NÃO RECOMENDADA**

### Fatos observados

- 106 físicas / 52 lógicas. `DatasetEntry` (modelo, `30-42`), `DatasetManifest`
  (registro imutável com `resolve()` e `aliases`, `45-71`), `_load_raw`
  (`74-94`), `load_manifest` (`97-105`, `@lru_cache`).

### Análise SRP

- Mistura modelo + registro (service leve) + loader + cache — mas é o padrão
  "loader de manifest" do pacote, coeso e pequeno. `DatasetManifest` é um
  registry com erro acionável (`resolve` com `KeyError` listando aliases,
  `64-67`). Dividir modelo/loader/registry em 3 módulos fragmentaria sem
  ganho: todos os motivos de mudança (formato do YAML, aliases, cache)
  co-evoluem. Cobertura 100% (10 testes em `test_manifest.py`). Consumidores
  em `resolution.py:25`, `engine/pipeline.py:17`, `excel/sintetico.py:74`,
  `cli/split.py:42`, `cli/measure.py:43`. Não dividir.

---

## 5. `config/categorias.py` — **NÃO RECOMENDADA**

### Fatos observados

- 104 físicas / 45 lógicas. 4 modelos Pydantic (`GrupoExecutorMode` `33-54`
  com `_check_exactly_one_filter` `46-54`, `WholeIndicatorMode` `57-61`,
  `CategoriaConfig` `69-72`, `CategoriasFile` `75-79`), `_load_raw` `82-91`,
  `load_categorias` `96-104` (`@cache`).

### Análise SRP

- Mesmo padrão loader+modelo de `manifest.py`/`catalog.py`; coeso e pequeno.
  A única regra (exatamente um de `in_values`/`catch_all_contains`,
  `46-54`) está contida no modelo — correto. Cobertura 100% (14 testes,
  incluindo os reais MinC/MTur em `test_categorias.py:144-194`). Consumidores
  `categoria_filter.py:20`, `cli/split.py:41`, `cli/measure.py:42`,
  `excel/sintetico.py:69`, `excel/inms_1_1_audit.py:40`. Não dividir.

---

## 6. `config/niveis.py` — **NÃO RECOMENDADA**

### Fatos observados

- 24 físicas / 6 lógicas. Apenas 2 constantes: `NIVEL_ORDER` (`niveis.py:17`)
  e `NIVEL_BY_CATEGORIA` (`niveis.py:19-24`). Sem classes/funções.

### Análise SRP

- Dado declarativo (mapa contratual Categoria → Nível), dono único do mapa,
  consumido por `excel/groups.py:17`, `excel/sintetico.py:76`,
  `excel/inms_1_1_audit.py:41`. Nenhum motivo para dividir; sequer é
  candidato de fato.

---

## 7. `config/_paths.py` — **NÃO RECOMENDADA**

### Fatos observados

- 16 físicas / 9 lógicas. Uma função: `reject_unsafe_relative_path`
  (`_paths.py:11-16`), validando contra `PurePosixPath`/`PureWindowsPath`
  para rejeitar absolutos e `..`.

### Análise SRP

- Segurança de fronteira (config não confiável não escapa de `data_dir`),
  compartilhada por `models.py:14` e `manifest.py:19`. 1 responsabilidade, 1
  função. Não dividir. (83%: linha 15 descoberta — ramo do `PureWindowsPath`.)

---

## 8. `config/catalogs/anexo_e.yaml` — **NÃO CANDIDATO** (dado)

- 688 linhas de dados puros (106 itens, extraído programaticamente, não
  digitado à mão). Sem lógica; consumido por `catalog.py`. Confirmado como
  dado, conforme o ticket.

---

## Plano incremental

1. **Testes antes**: cobrir os 4 ramos descobertos de `models.py` (97, 189,
   362, 369) em `tests/test_models.py`.
2. **Extração sem mudança de comportamento**: mover o bloco acceptance
   (`models.py:266-342`) → `config/acceptance.py` com reexport em `models.py`
   (API preservada).
3. **Validação**: `mypy src/pyauditor/config/` (limpo hoje),
   `ruff check`/`format`, e suítes completas de config.
4. **Nenhuma outra divisão** no pacote: `catalog.py`, `manifest.py`,
   `categorias.py`, `resolution.py`, `niveis.py`, `_paths.py` ficam como
   estão (falsos positivos / divisão reduziria clareza).

## Validações recomendadas

- `.venv/bin/python -m mypy src/pyauditor/config/` → `Success`.
- `.venv/bin/python -m ruff check src/pyauditor/config/` (26× E501 e 4× I001
  pré-existentes, estilo — não bloqueiam).
- `.venv/bin/python -m pytest tests/test_catalog.py tests/test_manifest.py
  tests/test_models.py tests/test_categorias.py tests/test_config_per_orgao.py
  tests/test_config_resolution.py tests/test_configs_shared_invariants.py -q
  --cov=pyauditor.config --cov-report=term-missing` → 53 passed.
- Pós-extração, incluir também as 7 suítes de acceptance:
  `tests/test_full_acceptance_smoke.py`, `test_remaining_ratio_indicators.py`,
  `test_precomputed_table.py`, `test_external_catalog_sum.py`,
  `test_count_difference.py`, `test_ratio_tracer_bullet.py`,
  `test_segmented_ratio.py`.