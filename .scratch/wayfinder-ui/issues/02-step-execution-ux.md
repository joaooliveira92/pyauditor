# 02 — Execução por etapa e UX de corrigir-e-tentar-de-novo

- **Type:** grilling
- **Status:** resolved
- **Blocked by:** —

## Question

O CLI tem `bootstrap`, `measure`, `report`, `consolidate`, `split`, `run` —
hoje só `run` é exposto (via subprocess, sem stdin). Decidido: passar a rodar
os subcomandos individualmente do lado do servidor (não simular TTY
interativo).

Resolver:

- Como o seletor de comando aparece no painel Pipeline existente (dropdown?
  abas?) e quais parâmetros cada subcomando precisa coletar além de
  competência/órgão (`--strict`, `--data-dir`, `--capa-path`, flags
  específicas de `measure`/`report`/`consolidate`/`split` — ver
  `src/pyauditor/cli/parser.py`).
- Semântica de "tentar de novo": ao falhar/ter warning numa etapa, o usuário
  corrige o formulário (ticket 01) e reroda só aquela etapa, ou a cadeia
  inteira desde o início? Como o estado de "etapa X falhou/passou" fica visível
  sem virar visualização de saída (que está fora de escopo)?
- Isso muda o contrato do endpoint `/api/pipeline` (hoje: um job = um comando
  fixo) — decidir a forma nova (um job por etapa? um job composto com
  sub-status?).

## Answer

Fatos que mudam o enquadramento: o estado resumível de `pyauditor run`
(`.pyauditor/runs/`, skip-se-`done`, callbacks `on_state_change`/`on_warning`)
só existe dentro do subcomando `run` — `bootstrap`/`split`/`measure`/`report`/
`consolidate` chamados direto são one-shots sem estado persistido. E
`server.py` é deliberadamente desacoplado do pacote `pyauditor` (roda `uv run
pyauditor` no ambiente do workspace-alvo, pra continuar "copie esta pasta pra
qualquer lugar") — então importar `execute_run` em processo pra reusar os
callbacks quebraria essa portabilidade e está fora de cogitação.

1. **Seletor de comando**: dropdown com os 6 subcomandos (bootstrap, split,
   measure, report, consolidate, run), default `run` (comportamento atual
   inalterado por default). Ao selecionar um step, mostrar só as flags que
   mudam *comportamento* daquele subcomando (`--strict`, `--final-month`,
   `--on-warning` em `run`) — não as de path (`--config-dir`, `--data-dir`,
   `--output-dir`, `--report-dir`, `--roms-dir`, `--capa-path`, `--manifest`),
   que ficam nos defaults porque o workspace já fixa esses caminhos
   implicitamente. Sem modo "power user" com todas as flags.

2. **Semântica de retry**: como só `run` tem resume persistido, "corrigir e
   tentar de novo" numa etapa isolada é simplesmente reinvocar aquele
   subcomando sozinho (barato — ex.: só `measure`), não a cadeia inteira. A UI
   mostra uma faixa de status por etapa (pending/running/passed/failed/warned)
   só pras etapas rodadas *nesta sessão* — efêmera, sem persistência no
   servidor (perdida ao recarregar, como o item de fog "Histórico de
   execuções" já registrava em aberto). É status apenas, não conteúdo do
   warning (isso é ticket 03) nem visualização de saída (fora de escopo do
   mapa).

3. **Contrato de `/api/pipeline`**: mantém um-job-por-invocação (forma atual).
   Só adiciona um campo `command` no payload (`bootstrap`/`split`/`measure`/
   `report`/`consolidate`/`run`, default `run`) ao lado de
   `competence`/`agency`/`force`/`clean` já existentes. O cliente é quem
   sequencia — um `POST` por etapa, correlacionado por `job_id` pra montar a
   faixa de status. O servidor não ganha um conceito de job composto/
   multi-etapa; fica tão simples quanto hoje.
