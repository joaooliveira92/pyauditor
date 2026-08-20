# 07 - Migração das capas .xlsx para CSV + objetos.csv como fonte de valores

Type: grilling
Status: open

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