# Relatório de auditoria SRP — repositório `pyauditor`

Pipeline de aferição do contrato 40/2022 (MinC/MTur). Auditoria estática de todo o código de
produção (`src/pyauditor/**/*.py`), **sem modificar nenhum arquivo**, segundo o spec
`.scratch/app-audit/spec.md`, consolidando as notas por pacote dos tickets 01–07
(`.scratch/app-audit/notes/`).

- Ferramentas disponíveis: `ruff` 0.16.3, `mypy` 2.3.1 (strict), `pytest` 9.1.1, Python 3.12.13.
- **Limitação registrada:** `radon`/`xenon` não instalados — toda complexidade ciclomática (cc) é
  **aproximada**, obtida por análise própria da AST (McCabe simplificado). Serve como sinal, não como
  métrica de ferramenta.
- Fato observado vs. hipótese é diferenciado ao longo do texto; incertezas são declaradas.

---

## 1. Resumo executivo

### Escopo

- **127 arquivos Python** no escopo de código do projeto: **68 de produção** (`src/pyauditor/`) +
  **59 de teste** (`tests/`). (Há 3 `*.py` fora desse escopo — `.agents/skills/…/scripts/*.py` e
  `.scratch/…/prototype/*.py` — não candidatos.) Código de configuração (`pyproject.toml`, CI) e
  recursos de dados (`config/catalogs/`) avaliados como não candidatos.
- **~26.600 linhas físicas** no total (`src` + `tests`); produção sozinha ≈ 15.900.

### Candidatos encontrados por prioridade

| Prioridade | Qtd. | Arquivos |
|---|---|---|
| **CRÍTICA** | 4 | `excel/inms_1_1_audit.py`, `orchestration/run.py`, `excel/sintetico.py`, `cli/measure.py` |
| **ALTA** | 7 | `orchestration/summary.py`, `logging.py`, `cli/main.py`, `excel/consolidate.py`, `interactive/flow.py`, `engine/pipeline.py`, `cli/split.py` |
| **MÉDIA** | 7 | `excel/report.py`, `orchestration/state.py`, `interactive/provider.py`, `config/models.py`, `rom/render.py`, `cli/report.py`, `engine/strategies/precomputed_table.py` (+1 achado transversal: duplicação de leitores CSV) |
| **BAIXA** | 8 | `periodo.py`, `excel/capa.py`, `cli/consolidate.py`, `excel/_style.py`, `excel/glosas.py`, `rom/summary.py`, `rom/loading.py`, `categoria_filter.py` (+ observações de seams) |
| **NÃO RECOMENDADA** | 36 | listados na seção 4 |

### Principais riscos arquiteturais

1. **God functions coordenadoras** em `excel/inms_1_1_audit.py` (1332 linhas), `excel/sintetico.py`
   (`write_sintetico_workbook`, cc≈32), `orchestration/run.py` (`execute_run` 293 linhas, cc≈22) e
   `cli/measure.py` (`run_measure` cc≈41) — domínio + orquestração + I/O + serialização no mesmo corpo.
2. **Duplicação de regra de negócio entre comandos**: cross-check `in_values`/`real_values` e warning
   de `outros` em `cli/measure.py:447-475` e `cli/split.py:291-312` (blocos praticamente idênticos).
3. **Presentação recalculando domínio**: `rom/render.py` recalcula a ressalva da penalidade no
   Markdown; `excel/sintetico.py` e `excel/consolidate.py` derivam aritmética dentro do renderer.
4. **Símbolos privados atravessando camadas**: `cli/measure.py:47` importa `_pipeline_version` de
   `engine/pipeline.py`; `rom/render.py:18` fura a seam de `engine.strategies._target`;
   `orchestration/run.py:53` importa `_SINTETICO_FILENAME` de `cli/split`.
5. **Dois mundos num arquivo**: `orchestration/summary.py` mistura modelagem JSON (máquina) com
   render Rich (humano). Duplicações de estado (precedência de exit-code, `_STATE_PRESENTATION`,
   parse de timestamp) espalhadas em 3+ módulos.

### Cinco arquivos com maior retorno potencial de refatoração

1. **`src/pyauditor/excel/inms_1_1_audit.py`** (CRÍTICA, 1332) — dividir por seções em subpacote
   `inms_1_1/` com fachada preservada.
2. **`src/pyauditor/orchestration/run.py`** (CRÍTICA, 1109) — extrair `plan.py`, `command_dispatch.py`
   e `resume.py`.
3. **`src/pyauditor/excel/sintetico.py`** (CRÍTICA, 970) — extrair `_stats`, verbatim e renderers por
   shape; dispatcher vira fino.
4. **`src/pyauditor/orchestration/summary.py`** (ALTA, 954) — separar modelagem JSON do render Rich.
5. **`src/pyauditor/cli/measure.py` + `cli/split.py`** (CRÍTICA/ALTA) — unificar o cross-check de
   categoria em `categoria_filter.py`; maior ganho cruzado do relatório.

---

## 2. Ranking dos candidatos

Ordenado por prioridade; dentro da mesma faixa, por retorno esperado (linhas físicas desc.,
pior complexidade primeiro).

### CRÍTICA

#### 2.1 `src/pyauditor/excel/inms_1_1_audit.py`

- **Prioridade:** CRÍTICA · **Linhas:** 1332 físicas / ~1100 lógicas · **Confiança:** alta
- **Principais funções:** `write_sheet` (:1213), `_write_section_*` (9 seções, de :131 a :1091),
  `_write_raw_block` (:270, cc≈16), `_normalize_no_prazo` (:252), `_build_grupo_rows` (:223),
  primitivas de célula/estilo (:131-218) — 22 funções top-level, 0 classes, 18 imports.
- **Responsabilidades identificadas:** regra contratual de prazo/tolerância do INMS 1.1
  (`_PRAZO_HORAS_CORRIDAS` :72-75); validação/normalização de dados (`_normalize_no_prazo`,
  `_write_raw_block`); resolução de grupos/categorias/níveis; serialização das 9 seções da aba em
  Excel (fórmulas, tabelas, formatação condicional, proteção).
- **Motivos independentes de mudança (5+):** leiaute de uma seção; regra de prazo/tolerância; estilo
  visual (:92-99); mecânica do Excel (tabelas/proteção/recalc); regra de meta/penalidade;
  vocabulário de grupos.
- **Sinais quantitativos:** maior do repo; 10 funções >40 linhas; cc 16 no raw block; 4 subpacotes
  importados.
- **Evidências qualitativas:** regra de negócio vive dentro do renderer; `_write_section_*` já têm
  assinatura regular `(sheet, rng, start_row) → next_row` (composição por cursor).
- **Dependências:** `cli/categoria_filter`, `config/niveis`, `periodo`, subpacote `excel` interno;
  consumido por `excel/sintetico.py`.
- **Risco da refatoração:** alto (artefato fiscal; 25 testes assertam verbatim). **Benefício:**
  alto — maior arquivo do repo, cada seção vira casa testável.

#### 2.2 `src/pyauditor/orchestration/run.py`

- **Prioridade:** CRÍTICA · **Linhas:** 1109 físicas / ~920 lógicas · **Confiança:** alta
- **Principais símbolos:** `execute_run` (:817-1109, 293 linhas, cc≈22); `_dispatch` (:566-679, 114
  linhas); `record_failure_and_decide` (closure, :891-949); `_ensure_state`; `_reconcile_state`;
  `dependency_missing`; `_own_artifact_missing`; `_cascade_skip`; `_plan`; `RunRequest`/`RunResult`.
- **Oito responsabilidades distintas** (topologia phase-major; validação de request; recuperação de
  estado; resolução de dependências; verificação de artefato; dispatch de comando; máquina de
  decisão de falha; relógio).
- **Motivos independentes:** adicionar fase/comando; contrato de entrada; schema de persistência /
  política de resume; pré-condições por comando; layout de saída de um comando; contrato de cada
  `cli.*`; política retry/skip/isolate/abort; injeção de tempo.
- **Sinais quantitativos:** >800 linhas; `execute_run` cc≈22 (limiar 40/10); 20 imports; tocar um
  comando novo atinge 6+ pontos do arquivo.
- **Sinais qualitativos:** coordena e também executa infra (persistir, decidir, dispatch); `_dispatch`
  conhece os contratos de todos os 5 comandos; `_own_artifact` conhece layout de arquivos de
  bootstrap/split/measure; `_now` não injetável.
- **Dependências:** `cli.*`, `config.resolution`, `excel.*`, `periodo`, `logging`, `state`, `capa_paths`.
- **Risco:** **alto** (núcleo do pipeline; 5 mocks em testes patcheiam `orchestration.run.run_measure`;
  `interactive` e `cli/run` dependem). **Benefício:** dar independência entre topologia, dispatch e
  resume; reduzir raio de impacto.

#### 2.3 `src/pyauditor/excel/sintetico.py`

- **Prioridade:** CRÍTICA · **Linhas:** 970 físicas / ~767 lógicas · **Confiança:** alta
- **Ações:** `write_sintetico_workbook` (:718, **253 linhas, cc≈32**) — dispatcher por INMS que escolhe
  renderer por `isinstance(calculation)` e por colunas; `_write_nao_ativado_sheet`, `_write_capa_*`,
  `_stats/_compute_stats`, 6 renderadores por shape.
- **Responsabilidades:** leitura/merge de abas verbatim; aritmética de estatísticas; política de
  warnings/degração por INMS; decisão de renderer; `atomic_write` final; aba “não ativado”.
- **Motivos independentes:** novo tipo de cálculo; mudança no formato das abas verbatim; mudança em
  “dentro do prazo”; mudança de colunas/formato; política de falha; ordem das abas.
- **Sinais:** 7 funções >40 linhas; 24 imports de 7 subpacotes; cc da coordenadora 32.
- **Dependências:** `config.*`, `engine.pipeline`, `categoria_filter`, `periodo`, `atomic_write` e
  6 módulos de `excel` internos. Consumido por `cli/split.py`.
- **Risco/benefício:** baixo-médio; coesão da `_stats` pura já permite extração de baixo risco.

#### 2.4 `src/pyauditor/cli/measure.py`

- **Prioridade:** CRÍTICA · **Linhas:** 684 físicas / ~271 lógicas · **Cobertura 77%** (mais baixa do
  pacote) · **Confiança:** alta.
- **God function `run_measure`** (:123-637, ~515 físicas, **cc≈41**); `_handle_result` (:264-367,
  escreve ROM .md/.json); `_hard_fail_todas_categorias`; `write_combined_roms` (:640-684).
- **Responsabilidades:** leitura/descoberta de configs e `categorias.yaml`; orquestração de dois
  caminhos (categoria-expandido em memória e `whole_indicator`); I/O via `measurement_source` da
  engine + hash de provenance; validação cross-check `in_values`×`real_values`; serialização
  (ROM `.md` + `.json`); apresentação extra.
- **Duplicação com `cli/split.py`** (fato): fallback `_shared`/`categorias.yaml` (:203-209, split
  :185-189); montagem de `per_inms` (:211-215, :197-201); cross-check (:447-475 = split :291-312);
  warning de “outros” (:543-554 / :377-386). A parte de cálculo já está em `categoria_filter.py`; o
  que duplicou são o pré-cálculo e as mensagens.
- **Motivos de mudança:** flag/formato do ROM; regra de categoria; layout dos sidecars; contrato do
  engine; mensagens de warning.
- **Dificuldade de teste (spec §12):** exige configs + datasets + `equipe.csv` reais; ramos não
  cobertos são os de erro da expansão em memória (:394-554).
- **Risco/benefício:** médio (coração do pipeline); primeiro passo recomendado é unificar a regra de
  categoria com o `split` (furado mais barato).

### ALTA

#### 2.5 `src/pyauditor/orchestration/summary.py`

- **ALTA** · 954 físicas / ~759 lóg · **Cobertura 78%** · **Confiança:** alta.
- **Ações:** `render_summary` (:877-954), `_result_panel` (:697-812, 116 linhas, cc≈12),
  `exit_code_for_run` (:146-183, precedência 1>4>3>0), `summary_json` (:642-694), `fmt_pt_br`
  (:542-598), TypedDicts.
- **Mundos misturados:** modelagem JSON (máquina/telemetria) × render Rich (humano). Helpers de
  leitura compartilhados pelos dois.
- **Duplicações:** precedência de exit-code repetida em `cli/results.py:98-109`; `_STATE_PRESENTATION`
  idêntico em `interactive/flow.py:66-72`; `_parse_run_timestamp` vs `state.py`.
- **Risco/benefício:** médio; separar `summary_json.py` permite testar schema sem Rich, e reusar
  `_organization_summary` sem acoplar a estilos.

#### 2.6 `src/pyauditor/logging.py`

- **ALTA** · 783 físicas / ~632 lógicas · **Cobertura 62%** (a mais baixa do pacote `orchestration`) · **Confiança:** alta.
- **Cinco responsabilidades:** política de severidade/verbosity; contrato de evento (`log_event`,
  `_RESERVED_CONTEXT_KEYS`, anti-secret `_SENSITIVE_KEY_FRAGMENTS`); serialização JSON
  (`_normalize_json_value`, cc≈18); adapter `_FlatJsonSink`; bridge do loguru (`setup_logging` :254-410,
  157 linhas, cc≈11, 7 params).
- **Motivos independentes:** mudar precedência `-v/debug`; mudar schema do evento; suportar novos
  tipos; mudar formato JSON; trocar a biblioteca de logging.
- **Dependências:** `loguru`; consumido por 9 módulos (5 dispatchs de `cli/main.py`).
- **Risco:** médio (risco de ciclo import se extrair com validador no mesmo módulo). Mitigação:
  extrair `log_contract.py` antes.

#### 2.7 `src/pyauditor/cli/main.py`

- **ALTA** · 737 físicas / ~312 lógicas · **Cobertura 92%** · **Confiança:** média-alta.
- **Três blocos grandes:** schema do parser (`build_parser` :222-364, 143 linhas); tradução fronteira
  argparse→request + validação (`_extract_*_request`, `_require`); dispatch/orquestração multi-órgao
  (`_dispatch_*`, `cli_main` :684-729, cc≈11).
- **Repetição do loop multi-órgao** em todo `_dispatch_*` (extrai request → valida → setup_logging →
  paths → loop → exit_code).
- **Dependências:** `orchestration.run` duplicando semântica; `config.resolution`, `loguru`.
- **Risco/benefício:** baixo-médio (arquivo bem coberto); extrair `parser.py`/`requests.py` evita
  ciclo (diferente de `dependencies.py` que já importa os `check_*`).

#### 2.8 `src/pyauditor/excel/consolidate.py`

- **ALTA** · 722 físicas / ~553 lísticas · **Confiança:** alta.
- **Responsabilidades:** leitura/merge de decisões (`read_existing_decisions` cc≈16); 5 builders de aba;
  **derivação financeira dentro do builder** (`build_glosas` :427, 144 linhas, cc≈18 — dedup, acúmulo,
  rateio, `compute_glosa` e escrita no mesmo loop); orquestração+logging.
- **Motivos:** um campo da decisão financeira muda; o layout de uma aba muda; o rateio muda;
  novas abas.
- **Risco/benefício:** médio; separar `_glosa_calcs` (domínio puro) de render mantém API.

#### 2.9 `src/pyauditor/interactive/flow.py`

- **ALTA** · 559 físicas / ~140 lógicas · **Cobertura 71%** · **Confiança:** alta.
- **7 responsabilidades** na UI: orquestração de telas (`_run_guided_flow`), formulário
  (`collect_answers`, 110 linhas), validação, catálogo+seleção de comandos
  (`select_commands`), política de reexecução (`_force_commands_for`), apresentação de estado,
  discriminador de falha (`_is_pre_dispatch_failure`, prefixo mágico).
- **Acoplamento real (fato):** é com `orchestration`+`periodo`, **não** com `excel`/`config`.
  `flow.py:30-43` → `provider`, `orchestration.run/state`, `periodo.month_bounds`.
- **Motivos:** campo de formulário; comando novo; ícone/estilo; contrato de frase do orchestrator;
  traduzir decisão de falha.
- **Risco/benefício:** médio-baixo; extrair `fields.py`/`commands.py`/`status_view.py` reduz `flow` a
  ~250 linhas.

#### 2.10 `src/pyauditor/engine/pipeline.py`

- **ALTA** · 505 físicas / ~420 lógicas · **Confiança:** alta.
- **5 responsabilidades:** modelos de resultado; leitura de config+injeção de órgão
  (`discover_config_files` cc≈14); acesso a CSV/arquivos (`resolve_source`, `load_rows`,
  `_detect_delimiter`); validação de colunas; orquestração `measurement_source`/`measure`.
- **6 motivos independentes** (formato, descoberta, colunas, fonte, quality gates, pipeline_version).
- **Acoplamentos privados:** `cli/measure.py:47` importa `_pipeline_version`; `cli/measure.py:488-519`
  reconstrói o resultado na mão (`_pipeline_version` is private).
- **Duplicação de leitor CSV:** `load_rows` vs `categoria_filter.read_raw_csv` (que normaliza header
  “Grupo executor”).
- **Risco/benefício:** médio ~ alto; split em `loading.py`/`discovery.py`/`version.py` mantém API por
  re-export e derruba o arquivo para ~250 linhas.

#### 2.11 `src/pyauditor/cli/split.py`

- **ALTA** · 439 físicas · **Cobertura 87%** · **Confiança:** alta.
- `run_split` (:145-439, cc≈40): load categorias; leitura/filtragem do dataset; cross-check duplicado com
  `measure`; escrita de CSV+config derivada; geração do `sintetico.xlsx` (via `excel/sintetico.py`).
- **Motivos:** regra de Categoria; leiaute dos artefatos `_split`; schema da config derivada;
  responsabilidade do relatório Excel.
- **Risco/benefício:** médio; unificar cross-check com `measure` e mover o bloco do `sintetico` para
  a camada Excel é o ganho cruzado mais barato.

### MÉDIA

**2.12 `excel/report.py`** — MÉDIA · 685 / ~479 · **Confiança:** alta. Coeso por aba; micro-ajustes
(domínio `compute_report_glosa` p/ `glosas.py`; `_inline_validation_formula` p/ `excel/_validation.py`).
**2.13 `orchestration/state.py`** — MÉDIA · 653 / ~520 · **Confiança:** alta. **Grande, porém coeso**
(schema do estado), divisão não recomendada; `_validate_command_entry` interna é candidata a
simplificação.
**2.14 `interactive/provider.py`** — MÉDIA · 436 / ~230 · **Confiança:** alta. **Adapter
`InteractionProvider`** coeso (Protocol; `ask_multi_choice` cc≈14); extrair `_guard_answer`/validators
no mesmo arquivo.
**2.15 `config/models.py`** — MÉDIA · 372 / ~206 · **Confiança:** alta. 28 dataclasses Pydantic
coesas; eixo útil de extração = bloco `acceptance` (`models.py:266-342`) consumido só nos testes
(produção anula `acceptance_test`). `_check_fields_for_aggregation` cc≈8, `_check_target_for_shape`
cc≈9 (limite interno).
**2.16 `rom/render.py`** — MÉDIA · 352 / ~121 · **Confiança:** alta. **Recalcula domínio no Markdown**:
`_render_ressalva_interpretativa` (:161-194) usa `shortfall` da engine + `math.floor/ceil`; hipótese do
ticket (“rom que lê a fonte e renderiza”) **refutada** — a leitura mora na engine; `render` só recebe o
`MeasurementResult`. CC do módulo ~15. `_MEMORIA_RENDERERS` faz `KeyError` cru (:267).
**2.17 `cli/report.py`** — MÉDIA · 263 / ~201 · **Confiança:** alta. `run_report` cc≈20, ~8 fontes
carregadas no mesmo corpo; carga+mescla de capa/responsáveis pode ser compartilhada com `consolidate`.
**2.18 `engine/strategies/precomputed_table.py`** — MÉDIA · 97 / ~70 · **Confiança:** alta.
`PrecomputedTableStrategy.calculate` (33-94, 62 linhas, **cc=22** — maior do pacote engine); quatro
motivos no mesmo método (parse de linha vazia; penalidade em três ramos; acumulador ponderado; headline
em três vias). Plano: extrair helpers privados `_row_result`/`_row_penalty`/`_headline` no mesmo
arquivo, sem mudar a API.

### BAIXA

**2.19 `periodo.py`** — BAIXA · 424 / ~326 (utilidade de competência, raiz). **Confiança:** alta. Não
mover de pacote (inverteria dependências). Div. interna opcional: `periodo_messages.py` é o único
motivo independente (texto/saudações).
**2.20 `excel/capa.py`** — BAIXA · 208 / ~127 · **Confiança:** alta. CSV I/O × render, dois motivos;
`capa_csv.py` + `capa_render.py` opcional.
**2.21 `cli/consolidate.py`** — BAIXA · 187 / ~94 · **Confiança:** alta. Coordena bem; mover
`_load_common_capa` para `excel/capa.py`.
**2.22 `excel/_style.py`** — BAIXA · 178 / ~96 · **Confiança:** alta. `_new_sheet`/`write_row` longas,
mas domínio único. Não urgente.
**2.23 `excel/glosas.py`** — BAIXA · 138 / ~84 · **Confiança:** alta. Cálculo (domínio) × I/O do
histórico — adiar até 2º consumidor.
**2.24 `rom/summary.py`** — BAIXA · 137 / ~74 · **Confiança:** alta. DTO do sidecar, coeso; higiene
(`assert` em produção, `import math` no corpo da função).
**2.25 `rom/loading.py`** — BAIXA · 52 / ~31 · **Confiança:** alta. Coeso (`load_summaries`,
`read_valor_base`); dep a vigiar: `rom → excel/objetos.py`.
**2.26 `categoria_filter.py`** — BAIXA · 132 / ~50 · **Confiança:** média. Guardião puro do domínio
Categoria; extrair a dupla de leitores CSV para `engine/loading` na etapa 3.

### Achados transversais

- **Duplicação de leitores CSV (MÉDIA):** `engine.pipeline.load_rows` e
  `categoria_filter.read_raw_csv` — riscos de drift; unificar em `engine/loading.py` (header
  normalizado vs bruto).
- **Seams furados (BAIXA):** `rom/render.py:18` importa `_target` privado; falta re-export de
  `as_float` na seam `strategies/__init__.py`; `engine/__init__.py` vazio (fachada vs vazio:
  decisão plausível).
- **String mágica entre camadas (BAIXA):** `"dependência não satisfeita:"` (run.py:1011) consumida
  em `interactive/flow.py`.

---

## 3. Plano sugerido por arquivo

Para cada candidato relevante: o que separar, para onde, o que fica, riscos, API e testes.

### 3.1 `excel/inms_1_1_audit.py` (CRÍTICA)

Novo subpacote `src/pyauditor/excel/inms_1_1/`:

| Módulo | Conteúdo movido |
|---|---|
| `_layout.py` | constantes de estilo/fonte/cor, formatos numéricos, colunas `_R.._AM`, `_SEM_NIVEL`, `_PRAZO_HORAS_CORRIDAS` |
| `_cells.py` | primitivas de célula/estilo (:131-218) |
| `_domain.py` | `_normalize_no_prazo`, `_build_grupo_rows`, `_REQUIRED_COLUMNS` |
| `_raw_block.py` | `_write_raw_block` (base R–AM) |
| `_sections_1_3.py` | `_write_section_1…3` |
| `_sections_4_5.py` | `_write_section_4…5` (detalhamento/subtotais) |
| `_sections_6_7.py` | `_write_section_6…7` (fora do prazo/auditoria) |
| `_sections_8_9.py` | `_write_section_8…9` (tempo/penalidade) |
| `write.py` | `_validate_write_sheet_params`, `write_sheet`, `has_required_columns` |

- `inms_1_1_audit.py` vira **fachada** (`__all__ = ("has_required_columns","write_sheet")`), 
  re-exportando de `write.py`. `sintetico.py` e testes não mudam.
- **Testes antes:** fixar os 25 testes de `tests/test_inms_1_1_audit.py` (876 linhas). **Depois:** suíte não
  editada roda verde; hipótese de equivalência byte-exata dos .xlsx a validar.
- **Ordem:** células → domínio → raw → seções (1 commit cada) → `write.py`.

### 3.2 `orchestration/run.py` (CRÍTICA)

1. `plan.py` — topologia (puro, sem efeitos): `_plan`, `_PHASE_ORDER`, `_SUPPORTED_ORGAO_SELECTORS`,
   `_downstream`.
2. `command_dispatch.py` — `_dispatch`, `dependency_missing`, `_own_artifact_missing` (concentra
   acoplamento a `cli.*`, `config.resolution`, `excel`, `capa_paths`).
3. `resume.py` — `_ensure_state`, `_reconcile_state` (depende de `state.*` e `plan.PlanStep`).
4. `run.py` mantém `RunRequest`/`RunResult`/`FailureDecision`/`execute_run`/closures/`_now` e
   **re-exporta** `dependency_missing` (e `PlanStep`); `__all__` inalterado.
5. **Mocks de teste:** apontar `test_orchestration_run.py:328,409,419,433` e
   `test_config_resolution.py:140` para o novo namespace (ou manter alias—não recomendado).
6. **Testes antes:** adicionar unitários de `_dispatch`/`dependency_missing`/`_own_artifact_missing`.

### 3.3 `excel/sintetico.py` (CRÍTICA)

- `sintetico/_stats.py`: `_Stats`, `_NivelAccumulator`, `_compute_stats`, `_format_*` (puro, sem openpyxl).
- `_verbatim_sheets.py`: `_write_csv_verbatim_sheet`, `_write_capa_sheet`.
- `_sheets/grupo_executor.py`, `whole_indicator.py`, `precomputed.py`, `ratio_aggregate.py`,
  `multi_ativo.py`, `nao_ativado.py`.
- `write_sintetico_workbook` vira **dispatcher fino** (~120 linhas); assinatura pública preservada
  (`cli/split.py` importa).
- **Testes:** `tests/test_excel_sintetico.py` (908 linhas) verde a cada passo; depois unitários
  para `_stats`.

### 3.4 `cli/measure.py` + `cli/split.py` (CRÍTICA/ALTA) — plano cruzado

1. **Antes:** cobrir os ramos descobertos de `measure` (:394-425/436-447/470-475/520-533/548-554) e os
   erros de escrita de `split` (:323-326/338-341/362-365).
2. **Unir a regra de categoria** em `categoria_filter.py`: `check_in_values_against_real(entries, real)`
   + warning `outros`, mantendo strings verbatim; `measure`+`split` consomem sem mudança de
   comportamento.
3. **Extrair escrita** do ROM/sidecar: `rom/writing.py` (`write_rom_artifacts`) usado por `_handle_result`;
   `split_writer.py` com `_write_filtered_csv`/`_derive_config`/`_write_derived_config`.
4. **Tirar Excel do CLI:** bloco `sintetico.xlsx` → `excel/sintetico.py:write_sintetico_for_competencia(...)`.
5. **API preservada:** `run_measure`, `MeasureResult`, `run_split`, `SplitResult`, `_SINTETICO_FILENAME`
   (importado em `orchestration/run.py:53`) continuam em seus lugares.
6. Alvo: `run_measure` <~150 linhas; cc≈41 → orquestrador fino.

### 3.5 `orchestration/summary.py` (ALTA)

- `summary_json.py`: `summary_json`, 5 TypedDicts, `_organization_summary`, `_result_for`, helpers de
  leitura, `_parse_run_timestamp`.
- `summary.py` mantem `render_summary`, `_result_panel`, `_command_table`, `fmt_pt_br`,
  `exit_code_for_run` (negócio de agregação), `_next_steps`.
- Deduplicações futuras: precedência `1>4>3>0` com `cli/results` via helper compartilhado;
  `_STATE_PRESENTATION` com `interactive/flow.py`; `_parse_run_timestamp` com `state.py`.

### 3.6 `logging.py` (ALTA)

1. `log_contract.py` — contrato+serialização, **sem loguru/sinks**: `_normalize_json_value`,
   `_format_text_value`, `_normalize_context`, `_validate_event`, constantes `_RESERVED_*`.
2. `log_json_sink.py` — `_FlatJsonSink`, `_format_timestamp`, `_format_level`.
3. `logging.py` fica: `logger`, `log_event`, `resolve_log_level`, `setup_logging`, `LoggingHandlers`,
   filtros. Nada público muda.

### 3.7 `cli/main.py` (ALTA)

- `cli/parser.py`: `build_parser` + factories de argumento.
- `cli/requests.py`: dataclasses `*Request` + `_extract_*_request` + `_require`.
  Sem import de volta para comandos (evita ciclo).
- `main.py` mantém `cli_main` + dispatch + `_each_orgao(...)` helper; reexporta `build_parser`.
- API: `cli_main`, `build_parser`, todos os `*Request` importáveis de `main.py` (`pyauditor/__init__.py:3`).

### 3.8 `engine/pipeline.py` (ALTA)

1. `loading.py`: `_detect_delimiter`, `resolve_source`, `load_rows` + (transforma o `read_raw_csv` em
   modo com cabeçalho normalizado). **Testes:** reforçar `test_pipeline_load_rows` (delimiter/alias/
   ragged).
2. `discovery.py`: `_ORGAO_CONTRACT`, `_inject_orgao`, `load_config`, `discover_config_files/configs`.
3. `version.py`: `pipeline_version()` público (quebra a importação privada em `cli/measure.py:47`).
4. `pipeline.py` mantém: `measurement_source`, `measure`, `_collect_config_columns`,
   modelos, e re-exporta os símbolos movidos.
5. Opcional (não especulativo): helper `measure_derived` para o caminho categórico hoje 
   remontado em `cli/measure.py:488-519`.

### 3.9 `excel/consolidate.py` (ALTA)

- `consolidate/_decisions_io.py`: `read_existing_decisions`, `_normalize`/`_no_duplicate`/`_renamed`,
  `_DECISION_COLUMNS`, `RowKey`.
- `consolidate/_glosa_calcs.py`: a aritmética de `build_glosas` (dedup, acúmulo, rateio, saldo)
  como função pura; `build_glosas` só renderiza o resultado.
- Fachada re-exporta `build_consolidated_workbook`/`read_existing_decisions` (API preservada).

### 3.10 `interactive/flow.py` (ALTA)

- `interactive/fields.py`: `FieldSpec` + `collect_fields` + validadores (`_validate_competencia` etc).
- `interactive/commands.py`: `_ALL_COMMANDS`, `_force_commands_for`, catálogo.
- `interactive/status_view.py`: `_STATE_PRESENTATION`, `_state_presentation`, `_render_state_line`.
- Débito registrado: `_is_pre_dispatch_failure` (string mágica) resolver fora, na orquestração nova
  `failure_stage`.

### 3.11 MÉDIA/BAIXA

- **`rom/render.py`:** extrair `penalty_interpretation(config, calculation) → PenaltyReadings` para
  `engine/strategies/_target.py` (já tem `shortfall`); `render` só formata; corrigir `KeyError`
  (:267) com `get + ValueError`; deduplicar título (`_rom_title`). Testes atuais de ressalva
  (`test_rom_render.py`) fixam as 3 leituras — ficam como rede.
- **`config/models.py`:** mover bloco acceptance (`:266-342`) para `config/acceptance.py` verbatim +
  reexport em `models.py` (`__all__` intacto). Testes de acceptance-7-suites não mudam.
- **`interactive/provider.py`:** `_guard_answer` + `_validate_option_tuple`/`_validate_choices`.
- **`excel/report.py`:** mover `_inline_validation_formula`/`_add_evidencias_validations` =>
  `excel/_validation.py`; depois `compute_report_glosa` → `glosas.py` (quando houver 2º consumidor).
- **`cli/report.py`:** `cli/report_inputs.py` só quando `consolidate` compartilhar a carga de capa /
  campos; senão adiar.
- **`orchestration/state.py`:** sem divisão; melhorar CC de `_validate_command_entry` internamente
  (opcional).
- **periodo/categoria_filter/glosa/capa/loading/summary:** ver plano de cada nota; sem splits.

---

## 4. Falsos positivos e arquivos grandes aceitáveis

**NÃO RECOMENDADA (dividir reduziria clareza ou fragmentaria — ver notas dos pacotes para o porquê):**

| Arquivo | Nota do pacote |
|---|---|
| `cli/bootstrap.py` (127) | único criador de capas+esqueleto, coeso |
| `cli/results.py` (121) | hub vocab de exit-codes; mover cria ciclo |
| `cli/run.py` (63), `cli/dependencies.py` (26), `codes.py` (49), `atomic_write.py` (29) | wrappers/registros coesos |
| `config/catalog.py`, `resolution.py`, `manifest.py`, `categorias.py`, `niveis.py`, `_paths.py` | loaders pequenos e coesos |
| `engine/strategies/{base,_filters,_numbers,_target,segmented_ratio,count_difference,external_catalog_sum}` | estratégia única / helpers já extraídos |
| `engine/quality_gates.py` | runner pequeno, coeso |
| `capa_paths.py` (27), `excel/equipe.py` (148) | coesos (1 função / parser de um CSV) |
| `interactive/__init__.py`, `rom/__init__.py` | `__all__`/fachada implícita; apenas observar |
| `excel/{orgao_consolidation (432), objetos (326), grupos, inms_base, _datetime, _workbook, prazos, _csv_verbatim, _safety}` | parsers / domínio puro e coeso |
| `rom/dedup.py` | 16 stmts; merge de resumo coeso; o anti-exemplo de fragmentação |
| Já discutidos como "grande, mas aceitável" | `orchestration/state.py` (653), `excel/report.py` (685) |

- **`excel/orgao_consolidation.py`** (432): função única, pura, validação explícita — tamanho vem de
  docstrings/saídas, não de acúmulo.
- **`config/catalogs/anexo_e.yaml`** (688): **dado**, não código — fora do escopo de SRP.
- **Testes**: 59 arquivos (~10.7k linhas), incluindo `test_inms_1_1_audit.py` (876) e
  `test_excel_sintetico.py` (908) — grandes porque espelham pipeline de integração, **não** são
  candidatos (spec §33, §213).
- **Total na seção: 36 arquivos.**

---

## 5. Plano incremental

Seguindo o ordenamento do spec (1 testes → 2 extrações → 3 reduções de dependência → 4 divisão →
5 nomes/APIs → 6 remoção de duplicações):

**Etapa 1 — Testes (taxa zero de risco)**
1. `measure`: ramos :394-554; `split`: erros de escrita; `logging`: `_normalize_json_value`/erros de
   setup; interactive: `_force_commands_for`/`_is_pre_dispatch_failure`; `pipeline_load_rows`
   (delimiter+alias+ragged); `models`: :97/:189/:362/:369; `quality_gates`: erro `id_column`.
2. Fixes isolados sem mexer em produção.

**Etapa 2 — Extrações puras (sem efeito)** — ordem:
1. Cross-check de categoria → `categoria_filter.py` (measure+split), com strings verbatim.
2. `config/acceptance.py`.
3. `engine/penalty_interpretation` + render.py só formata.
4. `log_contract.py` + `log_json_sink.py`.
5. Aritmética do `sintetico` (`_stats.py`) e da glosa (`_glosa_calcs`).

**Etapa 3 — Redução de dependências**: `measurement_source`/`measure_derived` na engine; união de
leitores CSV (`engine/loading.py`); remover `_pipeline_version` privado (via `version.py`).

**Etapa 4 — Divisão de módulos** — `engine/{loading,discovery,version}` → `cli/{parser,requests}` →
`orchestration/{plan,command_dispatch,resume,summary_json}` → `excel/inms_1_1/*` →
`interactive/{fields,commands,status_view}` → `excel/sintetico/_sheets`. Suficiente para
`run_measure/execute_run/write_sintetico_workbook` darem conta.

**Etapa 5 — Melhoria de nomes/API**: `pipeline_version()` público; `as_float` na seam de strategies;
`failure_stage` na orquestração; decidir fachada vs vazio em `engine/__init__.py` e `rom/__init__.py`.

**Etapa 6 — Remoção de duplicações**: precedência de exit-code; `_STATE_PRESENTATION`;
`_parse_run_timestamp`; título do ROM; `load capa` (report/consolidate/sintetico).

Cada etapa sai verde: `ruff check`, `mypy src tests`, `pytest -q`, `pytest --cov=pyauditor
--cov-branch` (gate 85%), e os "matches acceptance test" sem mudança de comportamento.

---

## 6. Validações recomendadas

Ambiente: `.venv/` (Python 3.12.13 · `ruff` 0.16.3 · `mypy` 2.3.1 strict · `pytest` 9.1.1 +
pytest-cov). Comandos exatos por etapa:

```bash
# a) Lint/format.
.venv/bin/ruff check src/ tests/
.venv/bin/ruff format --check src/

# b) Tipagem estrita (projeto já é strict no pyproject).
.venv/bin/mypy src/ tests/

# c) Testes do passo (sem cobertura p/ rapidez, addopts locais removidos via `-o addopts=""`).
.venv/bin/pytest <suítes do passo> -q -o addopts=""
# ex. Etapa 2.3 (engine):
# .venv/bin/pytest tests/test_pipeline_load_rows.py tests/test_measurement_source.py \
#   tests/test_multi_asset_discovery.py tests/test_cli_measure.py tests/test_cli_split.py -q

# d) Suíte completa + gate de cobertura 85% (branch).
.venv/bin/pytest --cov=pyauditor --cov-branch --cov-report=term-missing -q

# e) Verificação de foco por pacote (amostras executadas hoje):
#    cli:   .venv/bin/pytest tests/test_cli_*.py tests/test_codes.py tests/test_atomic_write.py \
#             -o addopts="" --no-cov -q                # 110 pass
#    config:.venv/bin/pytest tests/test_catalog.py tests/test_manifest.py tests/test_models.py \
#	       tests/test_categorias.py tests/test_config_*.py tests/test_configs_shared_invariants.py \
#             -q --cov=pyauditor.config --cov-report=term-missing   # 53 pass
#    engine: .venv/bin/pytest -q                                   # 506 pass / 34 skipped, 86.5%
#    excel:  .venv/bin/pytest tests/test_excel_*.py -o addopts="" --no-cov   # 169 pass
#    interm. .venv/bin/pytest tests/test_interactive_*.py -q --no-cov    # 11 pass
#    rom:    .venv/bin/pytest tests/test_rom_*.py -o addopts="" -q      # 127 pass
```

**Notas de execução observadas nesta auditoria:**
- `mypy` strict no escopo: `Success: no issues found`. `ruff` no escopo: avisos pré-existentes de
  estilo (E501 etc.) + alguns `S101` — **não** corrigidos (fora de escopo; E501/S101 são higiene).
- **Limitação fora do ferramental:** a CC é estimada (sem `radon`/`xenon`);
  equivalência de .xlsx pós-extração é hipótese a validar pela suíte (ver testes que verificam
  fórmulas); `branch coverage` completa só em `pytest --cov=...` do projeto.

---

_Relatório composto em 2026-08-22, síntese dos tickets 01–07 e do spec. Nenhuma alteração de código
foi produzida._