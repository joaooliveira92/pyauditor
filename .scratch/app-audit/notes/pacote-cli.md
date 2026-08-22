# Nota SRP — pacote `cli` (ticket 01)

Data: 2026-08-22 · Escopo: `src/pyauditor/cli/` + módulos de raiz vinculados
`codes.py` e `atomic_write.py`.

## 0. Métricas e limitações

- Ferramentas executadas: `ruff` (lint), `mypy` (strict) e `pytest` + cobertura
  das suítes `tests/test_cli_*`, `tests/test_codes.py`, `tests/test_atomic_write.py`.
- **Limitação registrada:** `radon`/`xenon` não estão instalados — a complexidade
  ciclomática (cc) abaixo foi obtida por análise própria da AST (método McCabe
  simplificado: `If`/`For`/`While`/`ExceptHandler` + operandos de `BoolOp`,
  computado no corpo da função sem contar funções aninhadas). Valor aproximado,
  usado como sinal, não como métrica de ferramenta.
- `mypy` strict (config do projeto): **limpo** para todos os arquivos do pacote.
- `ruff`: 144× `E501` (docstrings/lines > 80) + 5× `I001` (imports desordenados,
  auto-corrigíveis). Todo estilo pré-existente — **não** usado como evidência de SRP.
- `pytest`: amostra das suítes ligadas ao ticket roda com `-o addopts=""`:
  **110 testes passando**. Suíte completa verde conforme map.md.
- Linhas **físicas** = `wc -l`; linhas **lógicas** ≈ nós `ast.stmt` (instruções).
- Testes considerados: `test_cli_measure.py` (542), `test_cli_report.py` (584),
  `test_cli_consolidate.py` (523), `test_cli_split.py` (379), `test_cli_main.py`
  (360), `test_cli_run.py` (196), `test_cli_bootstrap.py` (94),
  `test_cli_dependencies.py` (56), `test_codes.py` (18), `test_atomic_write.py`
  (54).

## Resumo dos candidatos

| Arquivo | Prioridade | Linhas físicas / lógicas | Cobertura | Confiança |
|---|---|---|---|---|
| `cli/measure.py` | **CRÍTICA** | 684 / 271 stmts | 77% | alta |
| `cli/main.py` | **ALTA** | 737 / 312 stmts | 92% | média-alta |
| `cli/split.py` | **ALTA** | 439 / 185 stmts | 87% | alta |
| `cli/report.py` | **MÉDIA** | 263 / 123 stmts | 84% | média |
| `cli/consolidate.py` | **BAIXA** | 187 / 79 stmts | 89% | média |
| `cli/bootstrap.py` | NÃO RECOMENDADA | 127 / 56 stmts | suíte verde | alta |
| `cli/results.py` | NÃO RECOMENDADA | 121 / 47 stmts | 88% | alta |
| `cli/run.py` | NÃO RECOMENDADA | 63 / 12 stmts | n/d (thin) | alta |
| `cli/dependencies.py` | NÃO RECOMENDADA | 26 / 11 stmts | n/d (registry) | alta |
| `codes.py` | NÃO RECOMENDADA | 49 / 18 stmts | 100% | alta |
| `atomic_write.py` | NÃO RECOMENDADA | 29 / 17 stmts | 100% | alta |

---

## 1. `cli/measure.py` — **CRÍTICA**

### Fatos observados

- **Função God `run_measure`** — `measure.py:123-637`: **515 linhas físicas**,
  **cc ≈ 41** (AST). Concentra a execução inteira do comando em um só corpo, com
  funções aninhadas:
  - `_hard_fail_todas_categorias` `measure.py:236-262`;
  - `_handle_result` `measure.py:264-367` (104 linhas, cc ≈ 7) — escreve o ROM
    `.md`, o sidecar `.json` e decide status/log de cada indicador.
- **Múltiplas responsabilidades no mesmo corpo** (sinal arquitetural §1 do spec):
  1. descoberta/leitura de configs e de `categorias.yaml` (`measure.py:167-217`);
  2. orquestração da medição: caminho categoria-expandido em memória
     (`measure.py:379-555`) + caminho `whole_indicator` single (`measure.py:557-615`);
  3. I/O de dados: `measurement_source` do engine (`measure.py:385-393`) e
     `raw_csv_path.read_bytes()` p/ operação de hash de proveniência
     (`measure.py:498`);
  4. validação (cross-check `in_values` vs `real_values`) `measure.py:447-475`;
  5. serialização: escreve ROM `.md` (`measure.py:275-282`) e `.json`
     (`measure.py:284-288`);
  6. apresentação extra: `write_combined_roms` `measure.py:640-684` (render de
     markdown combinado via `render.py`).
- **Duplicação de regra de negócio com `cli/split.py`** (fato; trechos em comum):
  - fallback `_shared` → `categorias.yaml` por órgão: `measure.py:203-209` e
    `split.py:185-189`;
  - construção de `per_inms` (entradas `grupo_executor`): `measure.py:211-215` e
    `split.py:197-201`;
  - cross-check `in_values` × `real_values` (mensagem praticamente idêntica):
    `measure.py:447-475` e `split.py:291-312`;
  - warning de `outros`: `measure.py:543-554` e `split.py:377-386`.
  A parte de *cálculo* já foi fatorada em `categoria_filter.py`
  (`compute_categoria_values`, `base_config_stem`); o que ficou duplicado são o
  **pré-cálculo e as mensagens**, hoje vivendo nos dois comandos.
- **Dificuldade de isolamento em teste** (spec §12): cobertura da suíte dedicada
  em **77%** — a mais baixa do pacote. Os trechos não cobertos são exatamente os
  ramos de erro da expansão em memória: `measure.py:394-425`, `436-447`,
  `470-475`, `520-533`, `548-554`. Testar `run_measure` exige montar configs +
  datasets + `equipe.csv` reais (projeto de integração), pois o corpo é monolítico
  e não permite injetar engine/escrita. `tests/test_cli_measure.py` (542 linhas)
  compensa com integração, não com isolamento.

### Hipóteses (declaradas)

- H1: a expansão por categoria em memória e o cross-check são regra de **negócio
  reutilizável** (a mesma semântica de `split`), não detalhe de `measure` — o que
  faria de `measure.py` o lugar errado para mantê-las.

### Motivos independentes para mudança

1. adicionar/alterar uma flag de `measure` (formato do ROM, `strict`…);
2. alterar regras de categoria / `in_values` (efeito colateral em `split`);
3. alterar o layout/forma de gravação dos sidecars `.json`;
4. alterar o contrato do engine (`measurement_source` / `measure`).

### Plano sugerido

1. **Antes**: `tests/test_cli_measure.py` já existe; adicionar cenários para os
   ramos não cobertos (as linhas citadas) — erro de leitura para uma categoria,
   ausência da coluna `Grupo_executor`, exceção na medição por categoria,
   warning de `outros` — com fixtures de CSV/Categorias.
2. **Extração 1 (categoria, pura)**: estender `categoria_filter.py` com
   `check_in_values_against_real(entries, real_values)` (e a construção do
   warning de `outros`), unificando `measure`+`split`. Sem mudança de
   comportamento; strings de warning preservadas verbatim.
3. **Extração 2 (escrita)**: mover “escrever ROM `.md` + summary `.json` para um
   símbolo curto (ex.: função `write_rom_artifacts` num novo `rom/writing.py`),
   deixando `_handle_result` só com cálculo de status + build do dataclass.
4. **Extração 3 (orquestração)**: `run_measure` passa a iterar `configs` e a
   chamar os pontos acima; alvo: `run_measure` abaixo de ~150 linhas.
5. **API preservada**: `run_measure`, `MeasureResult`, `IndicatorOutcome`,
   `check_measure_ready`, `write_combined_roms` e `_MeasuredIndicator`
   (importado por `main.py:28`) permanecem — extração não muda contrato.
6. **Ordem segura**: 1 → 2 (produção intacta) → 3/4 com `pytest` +
   `tests/test_cli_measure.py` verde e gate de cobertura 85% do projeto.

### Risco/benefício

- Risco: `measure.py` é o coração do pipeline (usado por `orchestration/run.py`
  e CLI); extrações podem afetar fixtures de dados reais. Mitigação: extrações
  puramente mecânicas, sem tocar em `engine/`.
- Benefício: reduz a maior complexidade do pacote (cc ≈ 41), elimina duplicação
  com `split` e abre caminho para testes unitários isolados (sem fixtures de
  projeto inteiro).

---

## 2. `cli/main.py` — **ALTA**

### Fatos observados

- 737 linhas físicas / 312 stmts; 20 imports top-level; 28 símbolos de topo —
  faixa >500 do spec.
- **Três responsabilidades claramente distintas no mesmo arquivo**:
  1. **Schema do parser CLI** — `build_parser` `main.py:222-364` (143 linhas,
     cc = 1, alto fan-out de flags): só registra argumentos.
  2. **Tradução fronteira argparse→request + validação** — request dataclasses
     `main.py:74-126`; `_require` `main.py:140-148`; `_extract_{measure,split,
     report,consolidate}_request` `main.py:367-456`; `_extract_capa_path`
     `main.py:408-412`.
  3. **Dispatch + orquestração multi-órgão + logging** — `_dispatch_*`
     `main.py:463-681` (`_dispatch_measure` 50 linhas, `_dispatch_split` 51,
     `_dispatch_report` 40) e `cli_main` `main.py:684-729` (cc ≈ 11).
     Cada `_dispatch_*` repete o padrão: extrai request → valida competência →
     `setup_logging(_run_log_path(...))` → resolve `per_orgao_paths` → loop por
     órgão → reduz com `exit_code_for_results`.
- `_run_log_path` `main.py:415-426` acopla a convenção de arquivos de log do
  `loguru` à CLI (docstring longa registrando a política de retenção —
  conhecimento de infra misturado).
- **Orquestração duplicada com `orchestration/run.py`**: o loop multi-órgão em
  `_dispatch_bootstrap`/`_dispatch_*` espelha o que o orchestrator `execute_run`
  já faz. (Hipótese: a CLI poderia delegar a orquestração multi-etapa ao
  orchestrator quando `--orgao both`, sem quebrar o contrato `cli_main`.)

### Sinais quantitativos

- `build_parser` com 143 linhas; `cli_main` cc ≈ 11; 26 importações totais, 20
  top-level; máquina de comando com 6 ramos.
- Cobertura da suíte: **92%** (`tests/test_cli_main.py`, 360 linhas) — bem
  coberta, o que reduz o risco da refatoração.

### Motivos independentes para mudança

1. adicionar/alterar flag de um subcomando (edita `build_parser`);
2. criar um novo subcomando (edita `build_parser` + `_is_command` + `cli_main` +
   um `_dispatch_*`);
3. mudar política de logging/caminho de log (edita `_run_log_path` +
   `_dispatch_*`);
4. mudar a semântica do loop multi-órgão (edita todos os `_dispatch_*`).

### Plano sugerido

1. **Testes antes**: `test_cli_main.py` já cobre o dispatch end-to-end; usar como
   rede de segurança e adicionar asserts sobre mensagens ao extrair.
2. **Extrair o schema do parser**: novo `src/pyauditor/cli/parser.py` com
   `build_parser` + factories de argumento (`_add_orgao_argument`,
   `_add_strict_argument`, `_add_logging_arguments`). `main.py` reexporta
   `build_parser`.
3. **Extrair request + tradutores**: `src/pyauditor/cli/requests.py` com os
   `*Request` dataclasses + `_extract_*_request` + `_require`. Sem imports de
   volta para os comandos — evita o ciclo de importação (diferente de
   `dependencies.py`, que importa os `check_*`).
4. **Dispatch permanece em `main.py`** como handler de orquestração; o bloco
   repetido “loop de órgãos + log path” vira helper `_each_orgao(...)` no próprio
   módulo.
5. **API preservada**: `cli_main`, `build_parser`, `MeasureRequest`,
   `ReportRequest`, `SplitRequest`, `ConsolidateRequest` continuam importáveis de
   `main.py` (`__all__` intacto, `pyauditor/__init__.py:3` importa `cli_main`).
6. **Cuidado com ciclos**: `parser.py`/`requests.py` sem imports de volta para
   os comandos.
7. **Depois**: `pytest tests/test_cli_main.py` + suíte completa + `ruff` (correção
   dos `I001` só depois da extração).

### Risco/benefício

- Risco baixo-médio: arquivo bem coberto; `build_parser` é *wide* (muitas flags)
  e não complexo.
- Benefício: reduz `main.py` a ~250 linhas, separa o contrato CLI (parser +
  request) da orquestração e elimina duplicação de loop.

---

## 3. `cli/split.py` — **ALTA**

### Fatos observados

- `run_split` `split.py:145-439`: **295 linhas** físicas, **cc ≈ 40**.
- Responsabilidades no mesmo corpo:
  1. load de `categorias.yaml` + montagem de `per_inms` (`split.py:185-201`);
  2. leitura/filtragem do dataset bruto via `measurement_source`
     (`split.py:232-251`);
  3. validação cross-check `in_values` (`split.py:291-312`) — **idêntico ao
     bloco de `measure.py:447-475`**;
  4. I/O: escrita de CSV filtrado (`_write_filtered_csv` `split.py:95-104`) e da
     config derivada YAML (`_derive_config` `split.py:107-131` +
     `_write_derived_config` `split.py:134-142`);
  5. **apresentação Excel**: geração de `sintetico.xlsx` (`split.py:388-416`),
     delegada a `excel/sintetico.py` mas com paths/warnings por competência no
     comando;
  6. logging das mensagens por órgão.
- Usa `atomic_write` (`split.py:34`) e `write_sintetico_workbook`
  (`split.py:45`) — o comando conhece camada Excel.

### Cobertura

- `test_cli_split.py` = 379 linhas; cobertura de `split.py`: **87%**. Ramos
  descobertos: erros de escrita (`split.py:323-326`, `338-341`, `362-365`).
  `run_split` precisa de projeto completo de dados + combinação de
  `categorias.yaml` — difícil de isolar.

### Motivos independentes para mudança

1. regras de filtragem de Categoria (afetam também `measure`);
2. layout dos artefatos `_split` (paths);
3. schema da config derivada;
4. o relatório `sintetico.xlsx` (responsabilidade própria da camada Excel).

### Plano sugerido

1. **Antes**: suíte existente; acrescentar cenários de erro de escrita
   CSV/YAML.
2. **Unificar com `measure`** o cross-check e o warning de `outros` em
   `categoria_filter.py`, eliminando a duplicação.
3. **Extrair a persistência dos artefatos `_split`**: `src/pyauditor/cli/split_writer.py`
   (ou `cli/split/artifacts.py`) com `_write_filtered_csv`, `_derive_config`,
   `_write_derived_config` e resolução de paths; `materialize` segue só como
   parâmetro.
4. **Extrair `sintetico`**: mover o bloco `split.py:388-416` para
   `excel/sintetico.py` como função `write_sintetico_for_competencia(report_dir,
   competencia, ...)` (o `cli` não conhece Excel).
5. **API preservada**: `SplitResult`, `check_split_ready`, `run_split` e a
   constante `_SINTETICO_FILENAME` (importada por `orchestration/run.py:53`)
   permanecem em `split.py`.

### Risco/benefício

- Risco médio: `split` alimenta `measure` pelo disco (configs derivadas / CSVs
  filtrados) e é usado standalone e via `run`. A extração é mecânica e protegida
  pela suíte.
- Benefício: derruba cc ≈ 40 para um orquestrador fino, remove a dependência de
  Excel do `cli` e elimina a duplicação com `measure` (maior ganho cruzado do
  ticket).

---

## 4. `cli/report.py` — **MÉDIA**

### Fatos observados

- `run_report` `report.py:110-263`: 154 linhas físicas, cc ≈ 20. Orquestra,
  todas no mesmo bloco:
  1. validação de dependências (`check_report_ready` `report.py:70-86`);
  2. load + fusão das capas CSV (comum + órgão) (`_load_capa_fields`
     `report.py:89-107`);
  3. load de `equipe.csv` (responsáveis) (`report.py:171-173`);
  4. load de `objetos.csv` (valor monetário) (`report.py:176-182`);
  5. discover de configs p/ CADASTROS (`report.py:194-200`);
  6. histórico de glosa (`report.py:202-209`);
  7. montagem `build_report` + `compute_report_glosa` + `write_historico`
     (`report.py:211-241`);
  8. política de publicação do código 3 (`report.py:243-244`,
     `missing_publication_fields` `report.py:47-54`).
- **Sinais**: múltiplas fontes de dados (capa, equipe, objetos, configs,
  histórico, ROMs) carregadas no mesmo `run_report`; cc≈20; 263 linhas.
- **Cobertura**: 84% na suíte `tests/test_cli_report.py` (584 linhas — o maior
  arquivo de teste, mas espelhando o pipeline, forte integração).

### Hipótese

- Que o trecho “carga + fusão de capa + responsáveis + valor_base”
  (`report.py:158-191`) é reutilizável também por `consolidate.py` e pelo
  `interactive` — hoje em parte duplicado de forma menor.

### Motivos independentes para mudança

1. regras de criticidade dos campos de publicação;
2. formato da capa/`equipe` (CSV → outro);
3. schema do histórico de glosa;
4. montagem do Excel (já delegada em `excel/`).

### Plano sugerido

1. **Antes**: manter `tests/test_cli_report.py` verde como base (cobre o caminho
   normal e publicável).
2. Extrair `_load_capa_fields` + responsáveis + períodos para
   `cli/report_inputs.py` com os campos comuns que `report` pode compartilhar
   com `consolidate`.
3. Numa segunda passada, reunir a política de 3/4 junto ao `results.py` (fonte
   única de códigos de saída).
4. `report.py` só orquestra chamadas — alvo: `run_report` abaixo de ~80 linhas.
5. **API preservada**: `ReportResult`, `run_report`, `check_report_ready`,
   `missing_publication_fields` permanecem.

### Risco/benefício

- Risco médio: `report` é consumido pelo orchestrator (`orchestration/run.py:47-51`)
  e pela CLI; o acoplamento com `write_historico` (glosa financeira) é sensível.
- Benefício: clarear as ~8 fontes de dados e a política de saída 3/4, e preparar
  insumos compartilhados com `consolidate`.

---

## 5. `cli/consolidate.py` — **BAIXA**

### Fatos observados

- `run_consolidate` `consolidate.py:76-187`: 112 linhas físicas, cc ≈ 12.
  Delega bem: `load_summaries`, `read_capa_csv_fields`, `read_valor_base`,
  `build_consolidated_workbook`, `read_existing_decisions`, `atomic_write`. Cada
  responsabilidade é uma chamada isolada — coordenação limitada.
- Violação leve: mistura validação de dependência (`check_consolidate_ready`
  `consolidate.py:46-56`), I/O (`_load_common_capa` `59-73`) e a orquestração.
- Cobertura **89%** (`tests/test_cli_consolidate.py`, 523 linhas).

### Motivos independentes para mudança

- Corpo fino; mudanças costumam vir dos erros de negócio em `excel/`.

### Plano sugerido

- Considerar mover `_load_common_capa` para `excel/capa.py` (coesa com
  `read_capa_csv_fields`), o que também eliminaria a versão duplicada que o
  `report` faz desse load de capas. É um passo incremental opcional.

### Risco/benefício

- Baixo risco, benefício pequeno — mantê-lo como melhoria incremental, não
  urgente.

---

## 6. `cli/bootstrap.py`, `cli/results.py`, `cli/run.py`, `cli/dependencies.py` — **NÃO RECOMENDADO**

### Fatos observados

- `bootstrap.py` (127 linhas): `run_bootstrap` cria os 3 tipos de arquivo (capas
  comum + órgão + esqueleto `equipe.csv`) mas são **coesos** — a criação das
  capas é a responsabilidade única; cc≈6.
- `results.py` (121 linhas): vocabulário compartilhado (`validate_competencia`,
  `exit_code*`, `DependencyCheck`). É o **hub de imports** do pacote — todos os
  comandos importam daqui, e a estrutura evita reimportação reversa
  deliberadamente (docstring `results.py:113-121`). Mover pode criar ciclos.
- `run.py` (63 linhas): thin wrapper do orchestrator — já delega tudo.
- `dependencies.py` (26 linhas): registry puro `CHECKERS`.
- Mypy limpo e suítes verdes em todos.

### Plano

Nenhum. Registrar como falsos positivos — a divisão fragmentaria sem ganho.

---

## 7. Módulos de raiz: `codes.py` e `atomic_write.py`

### `codes.py` (49 linhas) — NÃO RECOMENDADO

- **Fato**: módulo puro e coeso, responsabilidade única de formatar e ordenar
  códigos contratuais INMS. 2 funções públicas (`format_inms_code`,
  `contractual_sort_key`); sem imports de domínio; cobertura total.
- **Consumidores** (fato): `rom/render.py:14`, `excel/report.py:34-35`,
  `excel/inms_base.py:17`, `excel/consolidate.py:26` + `tests/test_codes.py`.
- **Veredito**: falso-positivo; não dividir.

### `atomic_write.py` (29 linhas) — NÃO RECOMENDADO

- **Fato observável**: responsabilidade única de infraestrutura (gravação
  atômica via temp + `os.replace`). 1 função, sem dependências de `cli`;
  consumida em `excel/` (capa, report, glosas, sintetico, consolidate),
  `orchestration/state.py:31` e `cli/` (`bootstrap`, `split`, `consolidate`).
- **Módulo** exemplar de coesão — prova de que tamanho pequeno + responsabilidade
  única é o ideal; **não tocar**.

---

## 8. Classificação cruzada / achado principal

O achado de maior valor do pacote não é um arquivo, é a **duplicação de regra
entre `measure` e `split`** (load de `categorias.yaml` com fallback `_shared`,
montagem de `per_inms`, cross-check `in_values` e warning de `outros`). Ela
viola SRP nos dois arquivos e DRY. A `categoria_filter.py` já é declarada como o
“único lugar que mantém os dois comportamentos idênticos”
(`categoria_filter.py:6-7`), mas hoje só cobre o cálculo (`compute_categoria_values`,
`base_config_stem`) — não o pré-cálculo nem as mensagens. Consolidar esse trecho
único é o primeiro passo no caminho das duas god functions.

## 9. Ordem segura de execução (agregada)

1. **Reforçar testes**: cobrir os ramos descobertos de `measure`
   (`measure.py:394-425`, `436-447`, `470-475`, `520-533`, `548-554`) e de
   `split` (erros de escrita) antes de qualquer mexida.
2. **Unificar o cross-check de categoria** em `categoria_filter.py` (puro, sem
   I/O) — consumido por `measure` e `split` com zero mudança de comportamento.
3. Com o cross-check consolidado, **extrair o alvo de escrita de `measure`
   (`_handle_result`) e de `split` (writers)** — ambos mecânicos.
4. **Parser e requests de `main.py` separados** (`cli/parser.py`,
   `cli/requests.py`), mantendo `cli_main` intacto.
5. **Report inputs** (`cli/report_inputs.py`) só quando `consolidate` já
   consumir a mesma carga; senão, adiar.
6. Rodar `ruff`, `mypy` e `pytest` a cada passo.

## 10. Validações recomendadas

- `mypy src/pyauditor` (projeto já é strict).
- `ruff check src/pyauditor/cli src/pyauditor/codes.py src/pyauditor/atomic_write.py`
  — espera-se redução dos 144× E501 e dos 5× I001 conforme docstrings/imports
  ficarem concentrados (aplicar `--fix` apenas aos `I001`).
- `pytest` (suíte completa) e `pytest --cov=pyauditor --cov-report=term-missing`
  (gate de 85% do projeto) por etapa.
- Amostra executada nesta nota: `pytest <10 suítes do ticket> -o addopts=""` →
  110 passed; `mypy src/pyauditor/cli src/pyauditor/codes.py
  src/pyauditor/atomic_write.py` → limpo.