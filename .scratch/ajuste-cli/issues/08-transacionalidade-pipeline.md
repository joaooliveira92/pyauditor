# 08 - Transacionalidade do pipeline por órgão

Type: grilling
Status: resolved
Blocked by: 03, 04

## Question

O pipeline é **transacional por órgão** (uma falha/pendência no MTur não afeta o relatório do MinC) ou **transacional para a execução inteira** (qualquer problema numa etapa bloqueia as demais / o consolidado)? Graduado da névoa do mapa (ajuste-cli) quando 03 (códigos de saída) e 04 (resumo de estados) fecharam.

Questões em aberto:

- Mantendo `run --orgao both`: se o report do MTur falha (técnico), o MinC segue produzindo relatório limpo e o código global sai `1` (03 já responde o código)? Isso já é o comportamento hoje (`execute_run` trata cada Command independente e aborta só a cadeia do órgão?).
- O `consolidate` é o único ponto verdadeiramente transacional (exige os dois órgãos). Deveria haver uma flag `--continue-on-error` por órgão, ou a regra é "por órgão, sempre seguir"?
- O estado persistido (`runs/`) deve rastrear "consolidado parcialmente produzido"? (interage com 07 — CSV como fonte — e com a trilha de auditoria).
- Relação com `skipped` de produção (código 3, ticket 03): o resumo precisa apontar explicitamente "relatório do MTur não gerado — rodar de novo só para MTur".

Contexto: review.md §"Perguntas que eu levaria para a equipe" (processamento) e decisões de 03/04.

## Answer

**O pipeline passa a ser transacional por órgão** (não mais transacional para a execução inteira). Decisões:

1. **Isolamento de falha entre órgãos** (`run --orgao both`, modo não-interativo): uma falha técnica num órgão não impede o outro de completar suas etapas (bootstrap→measure→report). Hoje `_abort_on_failure` (`orchestration/run.py`) aborta o loop `for command, orgao in plan` inteiro na primeira falha, inclusive etapas do outro órgão ainda não tentadas — isso muda. Sem opt-out: não há (nem haverá) flag `--continue-on-error` — isolar por órgão é o único comportamento não-interativo.

2. **`consolidate` continua rígido**: exige relatórios `.xlsx` + sumários `.json` de **ambos** os órgãos existirem em disco, sem modo de consolidação parcial. Um "consolidado parcial" violaria a garantia central do mapa (nenhuma saída incompleta apresentada como resultado válido). Quando um órgão falhou com erro técnico, `consolidate` deve ser **pulado proativamente** (`skipped`, com mensagem explícita tipo "bloqueado — MTur falhou"), reaproveitando/estendendo o mecanismo `_cascade_skip` (hoje só ativo no modo interativo) para também disparar automaticamente no modo não-interativo — em vez de deixar `consolidate` tentar rodar e falhar genericamente por `check_consolidate_ready` ("dependência não satisfeita"). O exit code final continua `1` (FALHA) de qualquer forma, por precedência (ticket 03) — a mudança é só a clareza da mensagem.

3. **Resumo final acionável** (ticket 04): quando um órgão não completar, o painel deve apontar o próximo passo explícito — ex. "relatório do MTur não gerado (bootstrap falhou) — rode `pyauditor run --orgao MTur`" — em vez de deixar o usuário inferir isso do estado bruto.

4. **Resume em vez de reprocessar do zero**: reexecutar `run --orgao both` depois de uma falha isolada deve pular (resume) as etapas já `done` do órgão que completou, não reprocessar tudo. Isso exige mudar `run_run` (`cli/run.py:46`), que hoje fixa `force=True` incondicional (documentado em `cli/run.py:7-9`: "`run` always regenerates"). **Novo default: `force=False`** (resume, mesmo comportamento do fluxo interativo) — a checagem "já `done`/`skipped`, pula" (`orchestration/run.py:268`) passa a valer também no `run` não-interativo. Uma nova **flag `--force` explícita** é adicionada à CLI para quem precisa do reprocessamento total (ex.: depois de corrigir manualmente `capa.csv`/`objetos.csv` sem esperar por invalidação automática de cache).

**Sem impacto em CONTEXT.md/ADR**: as decisões são mecânica de orquestração (isolamento por órgão, resume/force, skip em cascata), não vocabulário de domínio novo. A definição existente de **Órgão** em `CONTEXT.md` ("a consolidação os funde apenas no passo `consolidate`") já é consistente com a decisão 2 acima, sem conflito. Nenhum ADR aberto — segue o precedente dos tickets 03/04, registrados só no próprio ticket.

**Fatos de código levantados nesta sessão** (linha de base para a implementação):
- `execute_run` (`orchestration/run.py:217-317`) percorre um plano phase-major sequencial (`bootstrap MinC, bootstrap MTur, measure MinC, measure MTur, report MinC, report MTur, consolidate`), não órgão-major.
- `on_failure` default no `run` não-interativo é sempre `_abort_on_failure`; modo interativo já oferece "Ignorar esta etapa" → `_cascade_skip` (`orchestration/run.py:320-337`), que propaga `skipped` só dentro do órgão da falha + `consolidate` (via `_downstream`, linhas 200-214).
- `exit_code_for_run` (`orchestration/summary.py:42-68`, ticket 03) já agrega "pior vence" globalmente (precedência 1>4>3>0) — nenhuma mudança necessária aqui.
- `check_consolidate_ready` (`cli/consolidate.py:44-54`) checa só existência de arquivo, não `publicable`/rascunho — um relatório rascunho já satisfaz a checagem hoje (mantido).
- Estado persistido em `.pyauditor/runs/<competencia>-<orgao_selector>.json` (`orchestration/state.py`) já tem granularidade por Command×órgão (`CommandStateEntry`), suficiente para o resume — nenhuma estrutura nova de "consolidado parcial" é necessária.
- `force` (`orchestration/run.py:58,268`) controla exclusivamente a checagem "já done/skipped, pula" — não afeta sobrescrita de artefatos por si só (isso é efeito colateral de reexecutar o Command).

## Implementado no código

Duas refinamentos surgiram só ao escrever os testes de regressão (não previstos na sessão de grilling — registrados aqui por transparência):

- **Nova `FailureDecision` `"isolate"`**, distinta de `"skip"`: reaproveitar `"skip"` diretamente teria feito `record_failure_and_decide` reclassificar o próprio comando que falhou de `error` para `skipped` — mascarando o código de saída `1` (FALHA) do ticket 03, porque `exit_code_for_run` só enxerga `status == "error"`. `"isolate"` (`orchestration/run.py::isolate_on_failure`, usada como `on_failure` padrão do `run` não-interativo) preserva `status="error"` no comando que falhou e cascateia (`_cascade_skip`/`_downstream`) só o downstream — mesma órgão + `consolidate` — igual a `"skip"`. `"skip"` continua existindo intacta para o modo interativo (decisão humana, correto reclassificar).
- **`RunRequest.force_commands`** (`orchestration/run.py`): resume (`force=False`) preserva o "já done, pula" genérico, mas `run_run` passa `force_commands=frozenset({"report", "consolidate"})` — sempre redespachados mesmo sem `--force`, porque são baratos de regenerar a partir dos ROMs já materializados e o resumo final (ticket 04) precisa de um `Result` fresco para reportar `publicable`/`glosa_calculada` corretos mesmo de um órgão cujas etapas anteriores foram puladas nesta invocação (sem isso, `_sumario_orgao` caía nos defaults otimistas e o painel mostrava `CONCLUÍDO`/exit `0` para um órgão que na verdade terminou rascunho). O fluxo interativo não passa esse campo (default `frozenset()`), sem mudança de comportamento lá.

Arquivos alterados: `orchestration/run.py` (`isolate_on_failure`, `force_commands`, decisões `"skip"`/`"isolate"` nos dois pontos de despacho), `cli/run.py` (`on_failure=isolate_on_failure`, `force` como parâmetro, `force_commands`), `cli/main.py` (`--force`), `orchestration/summary.py` (`_next_steps` aponta o órgão incompleto e o comando de rerun). Testes: `tests/test_cli_run.py` (resume/força/isolamento), `tests/test_orchestration_summary.py` (mensagem acionável). Suíte completa: 279 passed, mypy limpo nos arquivos tocados.