Type: research
Status: resolved

## Question

`GLOSAS` só verifica o teto de 30% mensal (`CAP_PCT` em `glosas.py`). Existe algum teto anual ou acumulado ao longo da vigência do contrato no Termo de Referência (equivalente a "Valor global anual" na capa) que limite a soma das glosas de todos os meses? Se existir, é outro item de estado entre competências, na mesma família de [[02-rollover-glosa-nao-consumido]] e [[03-reincidencia-nao-rastreada]] — talvez valha resolver os três juntos como "o pipeline precisa de um histórico persistente entre execuções mensais", em vez de três soluções pontuais.

## Answer

**Não existe um teto anual real e operável — só o teto mensal de 30% (com rollover, ver [[02-rollover-glosa-nao-consumido]]).** O TR tem uma segunda fórmula na mesma seção do item 35 (`07_modelo_de_gestao.html:965-1010`) rotulada "Desconto Regulatório_**Anual**" (`Desconto Regulatório_Anual = max[0; min(Desconto Máximo_Anual; Ajuste_NMS(%) × RB)]`), mas os termos `RB` e `Desconto Máximo Anual` não são definidos em nenhum outro lugar do documento (confirmado por grep no `.scratch/inms-pipeline-spec/research/12-glosa-item-35.md` §4, sem hits fora da própria fórmula) — tem cheiro de boilerplate de template genérico não adaptado a este contrato, inclusive porque destoa do resto do item 35, que é inteiramente mensal.

Recomendação (já registrada na pesquisa anterior, reafirmada aqui): tratar a fórmula mensal (`Ajuste_NMS = Σ Pontos × 0,001%`, teto 30%, rollover) como fonte de verdade; não implementar um teto anual até o gestor do contrato confirmar que a fórmula "Anual" é intencional. `CAP_PCT = 30.0` em `glosas.py` já reflete essa leitura corretamente — nenhuma mudança de código necessária por este ticket. Reabrir só se o gestor confirmar a fórmula anual como operativa.
