# 03 — Convenção de estruturação de warnings

- **Type:** grilling
- **Status:** resolved
- **Blocked by:** —

## Question

Hoje os warnings do pipeline são texto livre (ex.: `"INMS 1.1 (MinC/2026-06),
categoria ATENDIMENTO_N1: in_values [...] sem correspondência..."`), sem
ponteiro estruturado pra arquivo+campo de origem. Tornar isso acionável
provavelmente exige mudar o `pyauditor` em si (estruturar o warning na
origem), não só a UI.

Resolver: a convenção de estruturação — que forma um warning estruturado
assume (ex.: `{code, orgao, competencia, inms, categoria, config_path,
field}`), onde ela nasce no pipeline (mecanismo de `on_warning` em
`orchestration/_warning_decision.py` é o lugar certo?), e até onde vale a pena
ir agora vs. deixar como fog (ex.: mapear TODOS os warnings existentes de uma
vez, ou só os mais comuns primeiro).

Não decidir aqui o "clicar e abrir o campo" fim-a-fim — isso é o item de fog
"Deep-linking exato" no map, que só fica especificável depois desta decisão.

## Answer

Fato levantado que enquadra a decisão: hoje `server.py` só vê o pipeline via
o JSON de `--output json` (flag top-level, `src/pyauditor/cli/main.py`,
aplica a todos os subcomandos — não só `run`), porque, por decisão do ticket
02, `server.py` nunca importa `pyauditor` em processo. Esse JSON
(`summary_json()`, `src/pyauditor/orchestration/summary_json.py:371`) hoje
só carrega `'avisos'` como **contagem** — nunca o conteúdo do warning.
Estruturar o warning sem tocar esse schema é invisível pra UI.

1. **Forma do warning estruturado**: dataclass `Warning` com campos `code`
   (string estável por tipo de warning, ex. `"in_values_unmatched"`,
   `"outros_leftover"`, ou `"unstructured"` pro fallback), `message` (o texto
   pronto de hoje, pra log/CLI), `orgao`, `competencia`, `inms_key`,
   `categoria` (todos `str | None`). Sem `config_path`/`field` literal — o
   consumidor (UI) deriva o caminho do arquivo a partir da convenção de
   nomes já conhecida (`_shared/inms-NN.yaml` + `{orgao}/inms-NN.CATEGORIA.yaml`)
   quando precisar; isso é o mecanismo do item de fog "Deep-linking exato",
   não desta decisão.

2. **Representação**: `result.warnings` passa de `tuple[str, ...]` pra
   `tuple[Warning, ...]` em todo o pipeline (não uma lista paralela — duas
   fontes de verdade pro mesmo evento vão divergir). `Warning.__str__()`
   retorna `message`, preservando `logger.warning(w)` e o prompt interativo
   de `--on-warning` sem mudança visível.

3. **Escopo agora**: só as duas funções de `categoria_filter.py`
   (`unmatched_in_values_warnings`, `outros_warning`) nascem estruturadas —
   são o exemplo já citado no ticket e já carregam `orgao`/`competencia`/
   `inms_key`/`categoria` limpos. Os ~7 outros pontos de warning
   (`consolidate.py`, `report.py`, `split.py`, `measure_run.py`) continuam
   texto livre, embrulhados como `Warning(code="unstructured", message=...)`
   — mesmo tipo fluindo por `result.warnings`, sem migração forçada agora.
   Estruturar o resto vira item de fog.

4. **Wiring no canal machine-readable**: `summary_json()` ganha um campo
   novo `'warnings': [{code, message, orgao, competencia, inms_key,
   categoria}, ...]` (lista plana, sem agrupamento/dedup — isso é decisão de
   consumo da UI, não desta) ao lado de `'avisos'` (que continua sendo a
   contagem, inalterado). Sem isso, a estruturação não é visível pra UI:
   `server.py` só enxerga o pipeline pelo subprocess + `--output json`.
