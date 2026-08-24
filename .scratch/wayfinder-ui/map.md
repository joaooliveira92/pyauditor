# Wayfinder UI roadmap

- **Status:** charting
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

(nenhum ticket resolvido ainda)

- **Ticket 01 (formulário INMS):** protótipo em `src/ui/prototype-inms.html`
  (4 variantes, `?variant=A|B|C|D`); decisão de layout: **variante B** (duas
  telas, contrato → segmentos), escolhida em HITL — proto capturado na branch
  `prototype/inms-form`; a implementação do formulário real é follow-up.

## Not yet specified

- **Formulários para as demais famílias de config** (`categorias.yaml`,
  `datasets.yaml`, tabelas institucionais) — que campos, que UX, uma vez que o
  formulário INMS sirva de modelo. Revisitar depois do ticket 01.
- **Modelo de navegação da sidebar** quando existir mais de uma família de
  formulário — agrupar por tipo? por órgão? Pode nascer do ticket 01 (que só
  cobre INMS), mas as demais famílias ficam em aberto até lá.
- **Deep-linking exato** entre um warning específico e o campo do formulário
  que o causou — depende da convenção de estruturação (ticket 03); a mecânica
  de "clicar no warning e abrir o campo" só fica especificável depois dela.
- **Histórico de execuções passadas** — hoje se perde ao fechar a aba; se isso
  vale a pena persistir (mesmo que só na sessão do processo) ainda não foi
  discutido.

## Out of scope

- **Visualização de saída** (workbook, ROM, `reports/`) dentro da UI —
  confirmado fora do destino: o app serve só pra rodar o pipeline, não pra ver
  ou revisar resultado.
- **Apoio a decisão fiscal** (anistia, decisão fiscal) — mesma razão acima.
- **Formulário para CSS de workspace** — CSS fica raw; só é puramente
  estético, sem a mesma barreira de "não entendo o schema" que o YAML tem.
- **Deployment multi-usuário/hospedado** — app continua local, single-user,
  bind em `127.0.0.1`.
