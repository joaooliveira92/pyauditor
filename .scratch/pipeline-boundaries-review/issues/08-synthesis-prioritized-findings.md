Type: research
Status: open
Blocked by: 01, 02, 03, 04, 05, 06, 07

## Question

Consolide os achados dos tickets 01–07 (fronteiras config→engine, engine→orchestration, orchestration↔cli/interactive, rom→excel, excel report→consolidate, cli dispatch, interactive→orchestration) num único punch list priorizado, usando a ordem de severidade do skill `python-production-engineer` ("Regras de revisão de código": corretude/perda de dados → segurança/privacidade → concorrência/idempotência/transações → resiliência sob falha → compatibilidade/operabilidade → testes ausentes/frágeis → desempenho com evidência → clareza/manutenção → estilo). Para cada item: severidade, fronteira de origem (qual ticket), impacto concreto, e uma disposição recomendada (corrigir agora / vira ticket de follow-up / aceitar como fog deliberado). Marque explicitamente se algum achado, ao ser visto em conjunto com os outros, revela uma fronteira mais ampla que nenhum ticket individual cobriu sozinho (ex.: um problema que atravessa três pacotes em cadeia).

Aplique o skill `python-production-engineer` (ler `.agents/skills/python-production-engineer/SKILL.md` por inteiro) para julgar severidade.
