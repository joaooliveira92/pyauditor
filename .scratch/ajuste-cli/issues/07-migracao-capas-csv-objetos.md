# 07 - Migração das capas .xlsx para CSV + objetos.csv como fonte de valores

Type: grilling
Status: resolved

## Answer

Resolvido por grilling (HITL), Q1–Q9 todas aprovadas. Migração das capas Excel (.xlsx) para CSV, completa e implementada no código:

1. **Reparto de campos** (Q1): `capa.csv` (comun) = Número do contrato, Processo SEI, Empresa contratada, CNPJ da contratada, Objeto, Vigência. `capa_{orgao}.csv` (por órgão) = Órgão contratante atual, Competência, Períodos, OS/NF/data, Fiscais (técnico/requisitante/administrativo), Gestor, Versão, Data da análise, Situação. Os monetários (`Valor mensal vigente`, `Valor global anual`) saem das capas — ficam em `objetos.csv`.
2. **`bootstrap`** (Q2): garante os 3 CSVs (comum + por órgão pedido) de forma idempotente; "capa existente será reutilizada".
3. **Valor mensal** (Q3): fonte = `TOTAL MENSAL` de `objetos.csv`; a Σ dos itens é validada → WARNING (não bloquea); `Valor global anual` = `TOTAL MENSAL × 12` validado contra `TOTAL ANUAL` → WARNING.
4. **Dados por item** (Q4): coluna `Valor Mensal (R$)` em `SERVICOS_POR_ORGAO` (consolidado), mapeada por índice 1–9 (nunca por nome — os nomes divergem entre fontes).
5. **Ausente vs malformado** (Q5): CSV ausente = dado incompleto (report/consolidate seguem, glosa não calculada / rascunho); malformado = FALHA técnica (exit 1).
6. **Caminhos** (Q6/Q9): resolução desde `--data-dir` (`input/capa.csv`, `input/capa_{orgao}.csv`, `input/objetos.csv`); `--capa-path` sobrescreve o capa comum (`capa.csv`); os por-órgão nunca ganham flag própria.
7. **Normalização** (Q7): `objetos.csv` → `;`/`utf-8-sig`, igual às capas.
8. **Formato monetário** (Q8): `parse_brl_value` aceita `R$ 1.234,56`/`461.063,58`/`148205.54` → float; divergência → WARNING.
9. **`--capa-path`** (Q9): é o caminho completo do `capa.csv` (comum); o por-órgão deriva do mesmo diretório (família de capas).

**Implementação embarcada no mapa** (nota do esforço: ticket resolvido → mudança no código):
- `excel/capa.py`: `COMMON_FIELD_LABELS`/`ORGAO_FIELD_LABELS`/`FIELD_LABELS`; `bootstrap_capa_csv`, `read_capa_csv_fields`; `render_capa_sheet`/`SHEET_NAME`/`SITUACOES` sobrevivem (embed no report Excel); removido `read_valor_mensal_vigente`.
- **`excel/objetos.py`** (novo): `read_objetos` (itens + TOTAL MENSAL/ANUAL, validação Σ e ×12 → Warnings) e `parse_brl_value`.
- `cli/main.py`: `--data-dir` em bootstrap/report/consolidate; `_capa_path_for` deriva `capa_{orgao}.csv` do comum; defaults `input/`.
- `cli/bootstrap.py`: cria `capa.csv` (comum) + `capa_{orgao}.csv`.
- `cli/report.py`: merge capa comum+órgão; `valor_base` de `objetos.csv` (ausente → não calculada, exit 4; malformado → exit 1); `check_report_ready` verifica capa comum + do órgão.
- `cli/consolidate.py` + `excel/consolidate.py`: `valor_base`/`itens` desde `objetos.csv`; `build_capa` já não lê monetários de capas; `build_servicos` coluna `Valor Mensal (R$)`.
- `orchestration/run.py` + `interactive/flow.py`: novos caminhos.

**Nova fonte de dados**: `input/` é gitignore; `input/objetos.csv` (normalizado), `input/capa.csv`, `input/capa_MinC.csv`, `input/capa_MTur.csv` no repo de trabalho. Suíte 275 passed; mypy limpo.

## Question

Como o pipeline passa a consumir as **novas fontes de entrada CSV** — `objetos.csv`, `capa.csv`, `capa_MinC.csv`, `capa_MTur.csv` — abandonando `capa.xlsx`/`capa_MinC.xlsx`/`capa_MTur.xlsx` — e quem passa a ser a fonte de cada campo?

Diretriz dada pelo usuário:
- Abandonar as capas Excel (`.xlsx`); usar apenas os CSVs.
- Suprimir das capas individuais os valores que conflitam com `objetos.csv` (hoje: `Valor mensal vigente` e `Valor global anual` — o monetário vira do `objetos.csv`).
- Os campos comuns entre `capa_MinC.csv` e `capa_MTur.csv` devem constar **apenas** em `capa.csv`.

Estado atual do código:
- `cli/main.py`: defaults `capa.xlsx` / `capa_{orgao}.xlsx` (`_capa_path_for`) e flags `--capa-path`.
- `cli/bootstrap.py` (`bootstrap_capa` em `excel/capa.py`): cria a capa Excel em branco (idempotente).
- `excel/capa.py`: `FIELD_LABELS` (22 campos), `read_capa_fields`, `read_valor_mensal_vigente`; `report` embute a CAPA como 1ª aba.
- `cli/measure.py`, `cli/report.py`, `cli/consolidate.py`: consomem `read_capa_fields`.
- `excel/consolidate.py` `build_capa`: usa `Valor mensal vigente` de MinC/MTur para `valor_base` e rateio.
- `input/objetos.csv`: 9 itens contratuais do contrato 40/2022, `Valor Mensal` por item, total R$ 461.063,58/mês; total anual R$ 5.532.762,96.
- `config/manifest.py` já resolve aliases de datasets CSV (padrão reutilizável para carregar as capas CSV).

Decisões em aberto:
- Estrutura/colunas de `capa.csv` (campos comuns) e das capas individuais — espelhando o `FIELD_LABELS` atual, menos os monetários?
- Como o pipeline desbotar o `Valor mensal vigente` do `objetos.csv` (validar paralelo com o `TOTAL MENSAL`? dados por item ficam onde no consolidado/relatório?)
- `capa.csv` como entrada ou também gerado/validado pelo `bootstrap`?
- Codificação/delimitador (seguir o padrão `DatasetManifest` com `;`/`utf-8-sig`?); validação de campos obrigatórios.
- Impacto na criticidade por campo (ticket 02) — campos passam a viver em fontes distintas.
- Compat/erro se algum CSV ausente/malformado: qual o impacto em `bootstrap`/`measure`/`report`/`consolidate` (este ticket decide a camada de leitura; o código de saída fica com o ticket 03).

Depende de: ticket 01 (a fonte de valores muda o caso de "glosa não calculada" para contingência) e tickets 02/03 (criticidade/códigos sensíveis à fonte do dado).
Contexto: revisão em `.scratch/ajuste-cli/review.md` §2 (crrticidade campos) e §3 (mensagens de capa); diretriz de entrada dada pelo usuário Na sessão do ticket 01.