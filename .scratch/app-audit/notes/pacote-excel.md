# Nota — Ticket 04: análise SRP do pacote `excel`

Fonte: `.scratch/app-audit/spec.md` + `.scratch/app-audit/issues/04-pacote-excel.md`.
Domínio: renderização de workbooks do pipeline 40/2022 (sintético, relatório e consolidado).
Idioma: pt-BR.

## Método e validação executada

- Leitura integral dos 17 módulos de `src/pyauditor/excel/`.
- Métricas via `ast`/`tokenize` (linhas lógicas, statements, funções, classes, complexidade McCabe própria). **Limitação registrada:** `radon`/`xenon` não instalados — usei `ast` + análise estática, conforme `map.md` e spec §138.
- `ruff check src/pyauditor/excel/` (sem modificar nada): 265 erros **pré-existentes** (255× E501 em strings longas de fórmula, 7× S101, 2× I001) — estado atual do repo, não é introduzido aqui.
- `mypy` em `inms_1_1_audit.py` → limpo.
- `pytest` (`.venv/bin/pytest`) no subconjunto excel (11 arquivos de teste) → **169 passed** (13 skipped por amostragem de cobertura do subconjunto).
- **Nenhum arquivo de código foi modificado.**

Convenção: "físicas" = total de linhas; "lógicas" = linhas com token executável (sem linhas em branco, comentário e docstring), por `tokenize`.

## Visão do pacote

| Módulo | Físicas | Lógicas | Papel |
|---|---|---|---|
| `inms_1_1_audit.py` | 1332 | 1100 | Aba INMS 1.1 enriquecida (fórmulas + auditoria de prazo) |
| `sintetico.py` | 970 | 767 | Orquestração do workbook sintético multi-INMS |
| `consolidate.py` | 722 | 553 | Consolidado financeiro (5 abas) |
| `report.py` | 685 | 479 | Relatório mensal (6 abas) |
| `orgao_consolidation.py` | 432 | 224 | Domínio puro: consolidar MinC/MTur |
| `objetos.py` | 326 | 197 | Parser validado de `input/objetos.csv` |
| `capa.py` | 208 | 127 | CSV da capa + render da aba CAPA |
| `_style.py` | 178 | 96 | Estilos + `new_sheet`/`write_row` |
| `equipe.py` | 148 | 96 | Parser de `equipe.csv` + mapeamento |
| `glosas.py` | 138 | 84 | Domínio de glosa + histórico I/O |
| `groups.py` | 118 | 66 | Mapa indicador → grupo operacional |
| `inms_base.py` | 96 | 56 | Regra única da aba INMS_BASE |
| `_workbook.py` | 60 | 29 | Helpers genéricos de workbook |
| `_datetime.py` | 39 | 20 | `parse_dt` estruturado |
| `prazos.py` | 28 | 10 | Leitura verbatim de `prazos.csv` |
| `_csv_verbatim.py` | 27 | 11 | Leitura crua de CSV |
| `_safety.py` | 18 | 6 | Sanitização de fórmula |

Linhas não são critério isolado (spec §33); a análise abaixo baseia-se em coesão e acoplamento.

---

## Candidatos por prioridade

### CRÍTICA

#### 1. `src/pyauditor/excel/inms_1_1_audit.py` — 1332 físicas / 1100 lógicas; 587 statements; 22 funções top-level; 0 classes; 18 imports

**Funções principais** (referências `arquivo:linha`):
- `write_sheet` (inms_1_1_audit.py:1213, 120 linhas) — orquestradora das 9 seções;
- `_validate_write_sheet_params` (inms_1_1_audit.py:1177) — validação de fronteira;
- `_write_raw_block` (inms_1_1_audit.py:270, 152 linhas, cc=16) — base de apoio R:AM + cabeçalhos e fórmulas;
- `_write_section_1_identificacao` (inms_1_1_audit.py:424), `_write_section_2_resumo` (inms_1_1_audit.py:464), `_write_section_3_memoria` (inms_1_1_audit.py:523);
- `_write_section_4_detalhamento` (inms_1_1_audit.py:576, 84 linhas), `_write_section_5_subtotais` (inms_1_1_audit.py:662, 124 linhas);
- `_write_section_6_fora_prazo` (inms_1_1_audit.py:788, 73 linhas), `_write_section_7_auditoria` (inms_1_1_audit.py:863, **162 linhas**);
- `_write_section_8_tempo` (inms_1_1_audit.py:1027), `_write_section_9_penalidade` (inms_1_1_audit.py:1091, 84 linhas);
- `_build_grupo_rows` (inms_1_1_audit.py:223) — resolução grupos→(grupo, nível, categoria);
- `_normalize_no_prazo` (inms_1_1_audit.py:252) — validação S/N do campo "No prazo";
- primitivas de célula/estilo (inms_1_1_audit.py:131–218): `_section_bar`, `_label_value`, `_header_row`, `_add_table`, `_add_situacao_conditional_formatting`, `_protect_support_columns`.

**Responsabilidades identificadas** (todas no mesmo arquivo):
1. Regra de controle/prazo contratual do INMS 1.1 (`_PRAZO_HORAS_CORRIDAS`, inms_1_1_audit.py:72–75; tolerância via `_datetime.PRAZO_TOLERANCIA_MINUTOS`);
2. Validação e normalização de qualidade de dado (`_normalize_no_prazo`:252; e `_write_raw_block`:345–364 e coluna "Situação dos dados");
3. Resolução de grupos/categorias/níveis (importa `categoria_filter` e `config.niveis`, inms_1_1_audit.py:39–41 e 77–78);
4. Serialização das 9 seções da aba em Excel (fórmulas, tabelas nativas, formatação condicional, proteção, congelamento).

**Motivos independentes de mudança (5+):** mudar o leiaute de uma seção; mudar regra de prazo/tolerância; mudar estilo visual (constantes 92-99, larguras 1246-1261); mudar mecânica do Excel (tabelas/proteção/recalc); mudar regra de meta/penalidade (`_validate_write_sheet_params`); mudar vocabulário de grupos/categorias.

**Sinais quantitativos**: 10 funções com >40 linhas; `_write_raw_block` cc=16; `_write_section_7_auditoria` cc=10; imports de 4 subpacotes do projeto (categoria_filter, config, periodo, excel interno). **Sinais qualitativos de acoplamento**: a regra de negócio ("S/N", tolerância, situação dos dados) vive dentro do renderer; os estilos são constantes de módulo compartilhados por todas as seções (o que torna a extração uma decisão de layout, não de lógica).

**Fato observado vs. hipótese**: é **fato** que o arquivo é o maior do repo e que concentra validação de domínio + serialização; é **fato** que cada `_write_section_*` já é uma função coesa com assinatura regular `(sheet, rng, start_row) → next_row` (a docstring do módulo, inms_1_1_audit.py:17-22, descreve a composição por cursor). **Hipótese** — verificada por teste posterior — que a extração por seção não altera o arquivo xlsx resultante.

**Dependências**: é consumido por `sintetico.py` (que chama `has_required_columns` e `write_sheet`); os novos módulos não terão ciclo (nenhum deles importa `write_sheet`).

**O plano (seção Parte B)**: converter `inms_1_1_audit.py` em facade que reexporta `has_required_columns`/`write_sheet`, e mover para um subpacote `inms_1_1/` as constantes, as primitivas de célula, o raw block e os grupos de seções.

---

#### 2. `src/pyauditor/excel/sintetico.py` — CRÍTICA (970 físicas / 767 lógicas; 361 statements; 18 funções + 2 dataclasses; 24 imports)

**Responsabilidades (5 fundamentalmente distintas):**
1. **Dispatcher por INMS** — `write_sintetico_workbook` (sintetico.py:718, **253 linhas, cc=32**): itera por `per_inms`, decide o renderer conforme `calculation`/categoria (sintetico.py:850–953), gerencia warnings/degradações por-INMS (sintetico.py:785–814, 869–899), cria abas verbatim Capa/Equipe/Prazos (754–778), valida `atomic_write` final (sintetico.py:961–969);
2. **Abas CSV verbatim** — `_write_csv_verbatim_sheet` (sintetico.py:636), `_write_capa_sheet` (sintetico.py:671, anexa `objetos.csv` ao fim da "Capa");
3. **Aritmética de estatísticas** — `_compute_stats` (sintetico.py:169, cc=10), `_Stats` (sintetico.py:160), `_NivelAccumulator` (sintetico.py:234), `_format_*` (sintetico.py:201–231);
4. **Aba "não ativado"** — `_write_nao_ativado_sheet` (sintetico.py:254);
5. **Renderadores por shape** — `_write_grupo_executor_sheet` (sintetico.py:407) + `_write_subtotals` (sintetico.py:262), `_write_whole_indicator_sheet` (sintetico.py:460), `_write_precomputed_table_sheet` (sintetico.py:507), `_write_ratio_aggregate_sheet` (sintetico.py:570), `_write_multi_ativo_sheet` (sintetico.py:342, INMS 1.14).

**Motivos independentes**: (a) novo tipo de cálculo/renderer; (b) mudança no contrato das abas verbatim de `input/`; (c) mudança na definição de "dentro do prazo" (estatísticas); (d) mudança de colunas/formato; (e) política de falhas/degradação e warnings; (f) ordem das abas (spec §14.4).

**Sinais**: 7 funções >40 linhas; cc=32 na coordenadora; 24 imports de 7 subpacotes (`config.*`, `engine.pipeline`/`engine.strategies`, `categoria_filter`, `periodo`, `atomic_write`, e 6 módulos de `excel`). É o módulo mais **acoplado** do pacote: a seleção do renderer depende do introspection de `base_config.calculation` (`isinstance`) e da presença de colunas no CSV — lógica de seleção de renderer + regra de negócio no mesmo dispatcher.

**Coesão**: a `_stats`/`_format` é **pura** (sem openpyxl) e já poderia viver fora; os renderers são coesos por shape; a verbatim é genérica. Portanto o ganho é claro e baixo risco.

**Plano**: ver seção B.

---

### ALTA

#### 3. `src/pyauditor/excel/consolidate.py` — ALTA (722 / 553; 303 statements; 14 funções + 1 dataclass)

**Responsabilidades (4):**
1. **Leitura/merge de decisões fiscais** — `read_existing_decisions` (consolidate.py:208, 43 linhas, cc=16) + helpers de validação `_normalize_header` (consolidate.py:153), `_check_no_duplicate_headers` (consolidate.py:164), `_check_renamed_headers` (consolidate.py:183);
2. **5 builders de aba** — `build_capa` (consolidate.py:253, 69 linhas), `build_servicos` (consolidate.py:324), `build_inms_base` (consolidate.py:388), `build_glosas` (consolidate.py:427, **144 linhas, cc=18**), `build_calculo` (consolidate.py:582, 77 linhas);
3. **Derivação financeira dentro do builder** — `_faixa` (consolidate.py:416), `_glosa_bruto` (consolidate.py:573), rateio (consolidate.py:61), acúmulo de pontos/saldo/anistia dentro de `build_glosas` (consolidate.py:456–547);
4. **Orquestração + logging** — `build_consolidated_workbook` (consolidate.py:661) e o `logger.warning` (consolidate.py:714).

`build_glosas` mistura deduplicação de resumo (`deduplicate_summaries`, consolidate.py:453–454), decisão fiscal/anistia (_DECISION_COLUMNS, consolidate.py:99–108), acúmulo por órgão (consolidate.py:458–471), rateio de saldo (consolidate.py:482–526), chamadas a `compute_glosa` (consolidate.py:528–539) e, só então, escrita das linhas e do resumo agregado (consolidate.py:475–505, 550–568). Dois motivos de mudança claros: (a) a lógica da glosa pode mudar *sem* mudar a planilha (e já vive centralizada em `glosas.compute_glosa` — bom); (b) a aritmética de rateio/saldo é recalculada *no* renderer e acoplada à escrita.

**Confiança**: alta.

---

### MÉDIA

#### 4. `src/pyauditor/excel/report.py` — MÉDIA (685 / 479; 148 statements; 17 funções)

**Por que não é ALTA**: todas as builders são funções finas `_build_*_sheet` (report.py:275, 294, 436, 460, 494) com fábricas de linha próprias (`_inms_base_row` report.py:322, `_group_row` report.py:363, `_cadastros_row` report.py:178, `_evidencias_row` report.py:196); a separação persistência × construção é boa (`build_report` report.py:639 usa `atomic_write` + `build_report_workbook` report.py:545). É um módulo **coeso por aba**.

**O que está misturado (real)**: (a) domínio financeiro `compute_report_glosa` (report.py:387) vive aqui em vez de em `glosas.py`; (b) validação inline de fórmulas `_inline_validation_formula`/`_add_evidencias_validations` (report.py:213/242) é genérica.

**Proposta**: ajuste pontual (mover esses dois auxiliares para módulos de domínio/primitivas), **sem divisão estrutural** — dividir por aba agora criaria fragmentação sem uma responsabilidade nova clara. Confiança alta.

---

### BAIXA

#### 5. `src/pyauditor/excel/capa.py` — BAIXA (208/127)

**Duas responsabilidades independentes**: (a) CSV I/O (`capa_csv_text` capa.py:152, `bootstrap_capa_csv` capa.py:164, `read_capa_csv_fields` capa.py:176, labels 46–84); (b) render da aba (render_capa_sheet capa.py:99). Dois motivos de mudança independentes (formato do CSV × layout da aba). **Alternativa**: o módulo de 127 linhas lógicas se separaria em `capa_csv.py` + `capa_render.py`, com facade reexportando — baixo risco, benefício modesto. **Não urgente** (BAIXA).

#### 6. `src/pyauditor/excel/glosas.py` — BAIXA (138/84)

Mistura **regra de domínio** (cálculo: `compute_glosa` glosas.py:42, `competencia_anterior`, `janela_reincidencia`, `saldo_anterior_pct_de`, `houve_reincidencia`) com **I/O de estado** (`read_historico` glosas.py:120, `write_historico` glosas.py:126, `historico_entry` glosas.py:131). Dois motivos de mudança; módulo pequeno. **Adiável**: tirar o `json`+`atomic_write` e restringir a glosa ao cálculo puro quando houver segundo consumidor (hoje os consumidores são `cli/report.py` e `consolidate.py`). Manter agora.

#### 7. `src/pyauditor/excel/_style.py` — BAIXA (178/96)

`new_sheet` (_style.py:71, 63 linhas, cc=12) e `write_row` (_style.py:136, 43 linhas) são longas e fazem validação + escrita; mas o módulo é o **domínio único** "formatação comum de planilha". Separação `estilos` × `primitivas` é plausível futuro, não urgência.

---

### NÃO RECOMENDADA

- `orgao_consolidation.py` (432/224): função única `with_orgao_consolidation` pura, sem I/O. O tamanho vem de **validação explícita + docstrings** (9 helpers de `_validate_*`/`_require_*`). Dividir fragmentaria a narrativa de validação; o código é coeso (fato) por "domínio da consolidação". Prioridade NÃO RECOMENDADA, confiança alta.
- `objetos.py` (326/197) e `equipe.py` (148/96): parsers de **um** CSV com modelo+validação+leitura no mesmo arquivo — coesão alta. Dividir em `model`/`parser`/`io` fragmentaria sem ganho; manter. NÃO RECOMENDADA.
- `groups.py` (118/66), `inms_base.py` (96/56), `_datetime.py` (39/20), `_safety.py` (18/6), `_csv_verbatim.py` (27/11), `prazos.py` (28/10), `_workbook.py` (60/27): pequenos e coesos.

---

## Plano por arquivo, ordem segura

Ordem geral: (1) garantir que os testes de contrato existam e passem; (2) **mover** (sem mudar comportamento) símbolos para módulos novos; (3) rodar `mypy`+`ruff`+`pytest` a cada passo; (4) a API pública (exportada em `__all__`) nunca muda; (5) nenhuma dependência nova.

### A — `inms_1_1_audit.py` (CRÍTICA): extrair por seções para subpacote `inms_1_1/`

| Novo módulo | Símbolos movidos | Responsabilidade |
|---|---|---|
| `excel/inms_1_1/_layout.py` | constantes `TITLE_FONT.._UNLOCKED` (inms_1_1_audit.py:92–108), formatos numéricos (inms_1_1_audit.py:86–90), colunas `_R.._AM` (inms_1_1_audit.py:111–113), `_SEM_NIVEL`/`_AUDIT_REVIEW_LABEL` (inms_1_1_audit.py:79), `_PRAZO_HORAS_CORRIDAS` (inms_1_1_audit.py:72), `_DATA_QUALIDADE_OK` | constantes da aba |
| `excel/inms_1_1/_cells.py` | `_section_bar` (131), `_label_value` (143), `_header_row` (165), `_add_table` (174), `_add_situacao_conditional_formatting` (185), `_protect_support_columns` (198), `_raw_range` (127), `_ColumnRange` (120) | primitivas de célula/fórmula |
| `excel/inms_1_1/_domain.py` | `_normalize_no_prazo` (252), `_build_grupo_rows` (223), `_REQUIRED_COLUMNS` (60) | validação de segurança e resolução de grupos |
| `excel/inms_1_1/_raw_block.py` | `_write_raw_block` (270) | base de apoio R–AM |
| `excel/inms_1_1/_sections_1_3.py` | `_write_section_1…3` (424/464/523) | seções fixas |
| `excel/inms_1_1/_sections_4_5.py` | `_write_section_4…5` (576/662) | detalhamento por grupo + subtotai |
| `excel/inms_1_1/_sections_6_7.py` | `_write_section_6…7` (788/863) | fora do prazo + auditoria (quebrar `_write_section_7` em helper da amostra) |
| `excel/inms_1_1/_sections_8_9.py` | `_write_section_8…9` (1027/1091) | tempo + penalidade |
| `excel/inms_1_1/write.py` | `_validate_write_sheet_params` (1177), `write_sheet` (1213), `has_required_columns` (123) | fronteira + orquestração |

**API preservada**: `excel/inms_1_1_audit.py` vira **facade** com `__all__ = ("has_required_columns", "write_sheet")`, reexportando de `write.py`; `sintetico.py` não muda (já chama `inms_1_1_audit.write_sheet`/`has_required_columns`).

**Ordem passo-a-passo**: (1) fixar os 25 testes de `tests/test_inms_1_1_audit.py` (876 linhas); (2) criar `_layout`/`_cells` e reexportar; (3) `_domain`, `_raw_block`; (4) grupos de seções `_sections_*` um por commit; (5) `write.py`; rodar a suíte **sem editar testes** após cada passo. Testes depois: apenas se necessário, adicionar casos por seção (não antes, para não fragmentar mudanças).

### B — `sintetico.py` (CRÍTICA)

| Novo módulo | Símbolos movidos |
|---|---|
| `excel/sintetico/_stats.py` | `_Stats`, `_NivelAccumulator`, `_compute_stats`, `_parse_datahora`, `_format_duracao`, `_fmt_pt_br`, `_format_pct_bruto`, `_format_row` (sintetico.py:150–231) |
| `excel/sintetico/_verbatim_sheets.py` | `_write_csv_verbatim_sheet` (636), `_write_capa_sheet` (671) |
| `excel/sintetico/_sheets/grupo_executor.py` | `_write_grupo_executor_sheet` (407), `_write_subtotals` (262) |
| `excel/sintetico/_sheets/whole_indicator.py` | `_write_whole_indicator_sheet` (460) |
| `excel/sintetico/_sheets/precomputed.py` | `_write_precomputed_table_sheet` (507), `_PRECOMPUTED_COLUMNS` (493), `_meta_atingida_display` (503) |
| `excel/sintetico/_sheets/ratio_aggregate.py` | `_write_ratio_aggregate_sheet` (570) |
| `excel/sintetico/_sheets/multi_ativo.py` | `_write_multi_ativo_sheet` (342), `_write_ativo_subtotals` (300), `_INMS_1_14_CATEGORIA_ORDER` (142) |
| `excel/sintetico/_sheets/nao_ativado.py` | `_write_nao_ativado_sheet` (254) |

`write_sintetico_workbook` permanece como **dispatcher fino**: resolve config (`measurement_source`, linha 800), escolhe o renderer pelo tipo de `calculation`/colunas, acumula warnings, executa `atomic_write` — reduzindo de 253 para ~120 linhas. Não muda assinatura pública (`write_sintetico_workbook` consumido por `cli/split.py:write_sintetico_workbook`). Testes: `tests/test_excel_sintetico.py` (908 linhas, 18 testes) deve ficar verde em cada passo; depois, testes unitários para `_stats` em arquivo próprio. Ordem: `_stats` (puro) → `_verbatim` → renderers um por commit → dispatcher.

### C — `consolidate.py` (ALTA)

| Novo módulo | Símbolos |
|---|---|
| `excel/consolidate/_decisions_io.py` | `read_existing_decisions` (208), `_normalize_header` (153), `_check_no_duplicate_headers` (164), `_check_renamed_headers` (183), `_TRACKED_HEADER_NAMES` (150), `_DECISION_COLUMNS` (99), `_DECISION_TEXT_COLUMNS` (106), `RowKey` (138) |
| `excel/consolidate/_glosa_calcs.py` | parte de `build_glosas` (dedup 453–454 + acúmulo 456–547), `_glosa_bruto` (573), `_faixa` (416) |

`build_glosas` passa a aceitar um **resultado já calculado** (agregação pura em `_glosa_calcs`) e apenas renderiza. A aritmética das 4 outras abas já vive em funções próprias (coesa). API preservada: `cli/consolidate.py` continua importando `build_consolidated_workbook` e `read_existing_decisions` de `pyauditor.excel.consolidate` (facade reexport). Testes: `tests/test_excel_consolidate.py` (400, 21) verde + novos testes para `_glosa_calcs`.

### D — `report.py` (MÉDIA)

Não dividir. Mover `_inline_validation_formula`/`_add_evidencias_validations` para um módulo primitivo (ex.: `excel/_validation.py`) e, opcionalmente, `compute_report_glosa` para junto de `glosas.py` quando houver 2º consumidor. Passo seguro com os 19 testes de `tests/test_excel_report.py`.

### E — BAIXAS

- `capa.py`: opcional `capa_csv.py` + `capa_render.py` com `capa.py` facade; testes `test_capa.py` (117) verde.
- `glosas.py`/`_style.py`: manter; registrar ticket de acompanhamento para extração de `historico_io` do `rom`, quando houver 2º consumidor.

---

## Falsos positivos (arquivos grandes aceitáveis)

1. `orgao_consolidation.py` (432 linhas): **domínio puro com validação explícita**; o tamanho é resultado de guarda-clauses + docstrings, não de mistura de responsabilidade. Dividir reduziria a cadeia de validação (`_validate_pair_identity` → `_consolidate` → `_require_*`) sem ganho. Confiança alta.
2. `objetos.py`/`equipe.py`: parser de um único arquivo, cobrindo model+validação+leitura — 1 responsabilidade. Confiança alta.
3. `report.py` (685 linhas) — fica de fora da divisão estrutural por coesão alta: ver seção MÉDIA; apenas micro-ajustes.
4. `_style.py` (178): domínio único de estilo/primitivas; prioridade BAIXA.

## Fato observado vs. hipótese

**Fatos observados** (a partir do código):
- Números de linhas, `cc` (ast) e funções longas como acima;
- `write_section` compõe as 9 seções por cursor de linha (inms:1213–1327 chama em ordem e passa `next_row`);
- `write_sintetico_workbook` decide por `isinstance(base_config.calculation, …)` e por chave de INMS deduplicada (sintetico:825–959);
- `build_glosas` acumula + escreve dentro do mesmo loop (consolidate:456–568);
- `read_existing_decisions` faz leitura + validação de cabeçalhos hand-edited (consolidate.py:208–240);
- Nenhuma dessas mudanças quebra os consumidores dos CLI conforme `cli/*` e `excel/sintetico.py`.

**Hipóteses (a validar por execução posterior)** — não observadas neste relatório:
- Que um xlsx re-gerado após as extrações seja **byte-a-byte equivalente** ou, na pior hipótese, que os testes existentes (que verificam fórmulas/estruturas) comprovem equivalência;
- Que não haja ciclos de import nos submódulos (direção do plano apontada — validar no 1º `mypy`);
- Que a divisão objetiva melhore a manutenibilidade (predição qualitativa, não fato).

**Limitações**:
- `radon`/`xenon` indisponíveis — CC realizada por script `ast` próprio;
- execução de cobertura relativa apenas ao subconjunto excel; a suite completa não depende deste ticket.

## Comandos de validação

```bash
.venv/bin/ruff check src/pyauditor/excel/
.venv/bin/mypy src/pyauditor/excel/
.venv/bin/pytest tests/test_inms_1_1_audit.py tests/test_excel_sintetico.py tests/test_excel_consolidate.py tests/test_excel_report.py tests/test_capa.py tests/test_glosas.py tests/test_objetos.py tests/test_orgao_consolidation.py tests/test_equipe.py tests/test_excel_workbook.py tests/test_excel_safety.py -q
# suite completa:
.venv/bin/pytest -q
```