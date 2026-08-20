# 08 - Transacionalidade do pipeline por órgão

Type: grilling
Status: open
Blocked by: 03, 04

## Question

O pipeline é **transacional por órgão** (uma falha/pendência no MTur não afeta o relatório do MinC) ou **transacional para a execução inteira** (qualquer problema numa etapa bloqueia as demais / o consolidado)? Graduado da névoa do mapa (ajuste-cli) quando 03 (códigos de saída) e 04 (resumo de estados) fecharam.

Questões em aberto:
- Com `manter `run --orgao both`: se o report do MTur falha (técnico), o MinC segue produzindo relatório limpo e o código global sai `1` (03 já responde o código)? Isso já é o comportamento hoje (`execute_run` trata cada Command independente e aborta só a cadeia do órgão?).
- O `consolidate` é o único ponto verdadeiramente transacional (exige os dois órgãos). Deveria haver uma flag `--continue-on-error` por órgão, ou a regra é "por órgão, sempre seguir"?
- O estado persistido (`runs/`) deve rastrear "consolidado parcialmente produzido"? (interage com 07 — CSV como fonte — e com a trilha de auditoria).
- Relação com `skipped` de produção (código 3, ticket 03): o resumo precisa apontar explicitamente "relatório do MTur não gerado — rodar de novo só para MTur".

Contexto: review.md §"Perguntas que eu levaria para a equipe" (processamento) e decisões de 03/04.