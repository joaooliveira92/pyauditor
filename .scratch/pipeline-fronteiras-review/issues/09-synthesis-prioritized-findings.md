Type: grilling
Status: open
Blocked by: 01, 02, 03, 04, 05, 06, 07, 08

## Question

Todas as 8 fronteiras têm achados individuais (tickets 01-08). Roll them into a single priority-ordered punch list, usando a ordem de severidade do skill `python-production-engineer` ("Regras de revisão de código": corretude/perda de dados → segurança/privacidade → concorrência/idempotência/transações → resiliência sob falha → compatibilidade/operabilidade → testes ausentes/frágeis → desempenho (só com evidência) → clareza/manutenção → estilo).

Surface também padrões que atravessam mais de uma fronteira — ex.: se o mesmo tipo de "shape assumido sem revalidação" aparece em várias travessias, é um achado sistêmico, não N achados isolados.

Colete à parte, num bloco próprio, toda fricção concreta do modelo CSV+YAML registrada pelos tickets 01-08. Julgue: essa fricção, somada, é evidência suficiente para recomendar abrir um mapa wayfinder de decisão arquitetural dedicado ("CSV+YAML é o modelo certo, ou vale migrar")? Ou é pontual/rara demais para justificar isso agora — nesse caso, fica registrada como fog residual, não graduada? Esta é a decisão que resolve o item em "Not yet specified" do map.md.

Para cada punch-list item, decida: vira ticket/mapa de follow-up de implementação agora, ou fica deliberadamente adiado (com o motivo)? Grille o usuário nos itens onde severidade/prioridade contra restrições reais do projeto não for óbvia só pelo código.

Escreva o punch list final na `## Answer` deste ticket. O destino deste mapa é alcançado quando este ticket resolve — ele não implementa nada, só decide o que se desdobra.

## Answer

