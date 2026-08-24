# Wayfinder UI roadmap

- **Status:** resolved
- **Type:** wayfinder:map

## Destination

Evoluir `src/ui` (o app "Wayfinder", editor local — não confundir com a skill
`/wayfinder`) de um editor de texto YAML/CSS cru + botão único "Rodar" para uma
ferramenta local, single-user, que:

1. Apresenta as famílias de config YAML como **formulários específicos por
   tipo** — começando pelo indicador INMS (`_shared/inms-NN.yaml` +
   `{orgao}/inms-NN.CATEGORIA.yaml`) — em vez de texto YAML cru. O usuário não
   deve sentir que está editando YAML.
2. Expõe **todos os subcomandos** do pipeline (`bootstrap`, `measure`,
   `report`, `consolidate`, `split`, `run`) via um seletor dentro do painel
   Pipeline existente, executados **etapa a etapa do lado do servidor** —
   habilitando um loop de corrigir-e-tentar-de-novo sem re-rodar tudo.
3. Torna os **warnings do pipeline estruturados e acionáveis** — hoje são
   texto livre sem ponteiro pra arquivo+campo.
4. Migra o CSS próprio do app pra **Tailwind CSS via standalone CLI** (sem
   npm), output compilado e versionado.

Testes para `server.py` (validação de path/tamanho, lógica de execução por
etapa) entram no escopo.

**Fora de escopo:** visualização de saídas do pipeline (workbook, ROM,
`reports/`) e qualquer apoio a decisão fiscal (anistia, decisão fiscal) dentro
desta UI; edição de `.css` de workspace (ex.:
`docs/termo_de_referencia/styles.css`) continua raw; deployment
multi-usuário/hospedado.

## Notes

- Domain: pyauditor (contrato 40/2022 MinC/MTur) — ver `CONTEXT.md` raiz para
  vocabulário (INMS, categoria, órgão, competência etc.). Repo é single-context
  (sem `CONTEXT-MAP.md`); nenhum termo novo de domínio de negócio surgiu deste
  esforço — vocabulário de ferramenta (formulário, execução por etapa, warning
  acionável) é UI/tooling, não pertence ao `CONTEXT.md`.
- `docs/agents/issue-tracker.md` define as convenções do tracker local usadas
  aqui.
- Tickets de formulário: chamar Skill `prototype` (HITL) pra levantar
  fidelidade antes de travar layout/campos.
- Ticket de convenção de warnings: chamar Skill `grilling` — é decisão de
  arquitetura que toca `pyauditor`, não só a UI.
- Fatos já levantados (não precisam de novo research): CLI tem
  `on_warning` (`continue`/`retry`/`abort`) hoje só interativo via terminal —
  `server.py` roda `run` num subprocess sem stdin, então "pausar e corrigir"
  exige rodar comandos etapa a etapa do lado do servidor, não simular TTY.
  Famílias de config: (a) indicador INMS, (b) `categorias.yaml`, (c)
  `datasets.yaml`, (d) tabelas institucionais (`ajuste_inms`, `anexo_e`,
  `dados_contratuais`, `desconto_regulatório`).

## Decisions so far

<!-- one line per closed ticket -->

- **Ticket 01 (formulário INMS):** protótipo em `src/ui/prototype-inms.html`
  (4 variantes, `?variant=A|B|C|D`); decisão de layout: **variante B** (duas
  telas, contrato → segmentos), escolhida em HITL — proto capturado na branch
  `prototype/inms-form`. Follow-up (formulário real) implementado: backend em
  `src/ui/inms.py` + endpoints `/api/indicators` e `/api/indicator`, frontend em
  `index.html`/`app.js` — sidebar agrupa por indicador, painel central renderiza
  contrato + segmentos por órgão como formulário, save escreve de volta os YAMLs.
- **Ticket 02 (execução por etapa):** dropdown com os 6 subcomandos (default
  `run`), só flags de comportamento por etapa (não path); retry reinvoca só o
  subcomando isolado (sem resume — só `run` tem estado persistido); faixa de
  status por etapa é efêmera/sessão, sem persistência; `/api/pipeline`
  ganha só um campo `command` no payload, servidor continua um-job-por-
  invocação, cliente sequencia. Ver `.scratch/wayfinder-ui/issues/02-step-execution-ux.md`.
- **Ticket 03 (convenção de warnings):** dataclass `Warning{code, message,
  orgao, competencia, inms_key, categoria}` (sem path literal — consumidor
  deriva pela convenção de nomes) substitui `str` em `result.warnings`;
  estrutura agora só `categoria_filter.py` (`unmatched_in_values_warnings`,
  `outros_warning`), resto fica `code="unstructured"`; `summary_json()`
  ganha campo `'warnings'` com a lista estruturada, ao lado de `'avisos'`
  (contagem, inalterado) — sem isso a estruturação seria invisível pra UI,
  já que `server.py` só vê o pipeline via `--output json` do subprocess. Ver
  `.scratch/wayfinder-ui/issues/03-warning-structure.md`.
- **Ticket 04 (setup Tailwind):** `scripts/build-css.sh` baixa o CLI
  standalone pinado (`v4.3.3`) pra `.tailwindcss-cli/` (gitignored) e compila
  `src/input.css` → `styles.css` (sem `tailwind.config`, CSS-first); só
  importa `tailwindcss/utilities` com `@source` restrito a `*.html` (evita o
  CLI varrer README/app.js por palavras soltas); CSS atual preservado
  verbatim em `src/input.css`, então o `styles.css` gerado hoje é
  visualmente idêntico ao anterior — utilities ficam disponíveis pra
  formulários futuros. Ver `.scratch/wayfinder-ui/issues/04-tailwind-setup.md`.
- **Ticket 05 (plano de testes para `server.py`):** cobrir toda a superfície
  atual do servidor já nesta rodada (`resolve_file`, `GET`/`PUT /api/file`,
  `POST`/`GET`/`DELETE /api/pipeline` como hoje — o campo `command` do
  ticket 02 entra depois como diff pequeno, não suíte nova); `pytest`
  (portabilidade de `src/ui` é runtime, não onde os testes rodam);
  `tests/test_ui_server.py` na raiz, não `src/ui/tests/` próprio, porque
  `testpaths = ["tests"]` no `pyproject.toml` só pega a raiz por padrão. Ver
  `.scratch/wayfinder-ui/issues/05-server-test-plan.md`.
- **Ticket 06 (histórico de execuções):** vale expor — dado já existe em
  `App.jobs`, só falta listagem. Lista curta (~20 execuções), cap com evict
  do mais antigo, dobrado no painel Pipeline existente (lista colapsável,
  sem aba separada), novo `GET /api/pipeline` de listagem (id + resumo)
  ao lado do `GET /api/pipeline/<job_id>` existente (inalterado). Ver
  `.scratch/wayfinder-ui/issues/06-run-history.md`.

## Not yet specified

(vazio — toda a névoa graduou; ver "Graduado pra outros maps" abaixo e o
ticket 06 acima.)

**Graduado pra outros maps:**

- **Formulários para as demais famílias de config** + **modelo de
  navegação da sidebar** — resolvidos pelo map `config-forms` (formulários
  de `categorias.yaml`, `datasets.yaml`, bundle "Contrato"; sidebar
  agrupada por família).
- **Deep-linking exato** entre um warning e o campo do formulário que o
  causou — graduou pro map `warning-deep-link`
  (`.scratch/warning-deep-link/map.md`).

## Out of scope

- **Visualização de saída** (workbook, ROM, `reports/`) dentro da UI —
  confirmado fora do destino: o app serve só pra rodar o pipeline, não pra ver
  ou revisar resultado.
- **Apoio a decisão fiscal** (anistia, decisão fiscal) — mesma razão acima.
- **Formulário para CSS de workspace** — CSS fica raw; só é puramente
  estético, sem a mesma barreira de "não entendo o schema" que o YAML tem.
- **Deployment multi-usuário/hospedado** — app continua local, single-user,
  bind em `127.0.0.1`.
