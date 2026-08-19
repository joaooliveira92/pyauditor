Type: research
Status: resolved

## Question

`docs/spreadsheet.md` diz explicitamente: "a fórmula de glosa somente será fechada após a identificação completa da tabela ou metodologia de ajuste do Termo de Referência. O resultado técnico pode ficar abaixo da meta sem que o percentual financeiro seja arbitrado manualmente." O Anexo D (Tabela 28, item de contexto) também cita "as especificações do item 35 do Termo de Referência" como a referência para conversão de pontuação de penalidade em desconto (glosa) sobre o pagamento mensal.

Localizar o item 35 nos arquivos de `/Users/joao/dev/pyauditor/docs/termo_de_referencia/` (provavelmente em `07_modelo_de_gestao.html` — não confirmado, procurar por "35" ou "glosa" nos arquivos numerados 00 a 13) e responder:

1. Qual a fórmula/tabela de conversão de "pontuação de penalidade total" (soma dos `penalty_points` de todos os INMS do mês) em valor de glosa (R$ ou % do valor mensal do contrato)?
2. Existem faixas de desconto (ex: até X pontos = Y%, acima = Z%), teto de glosa mensal, ou é uma fórmula contínua?
3. A glosa é calculada por indicador individualmente e depois somada, ou só a pontuação total do mês entra na fórmula de conversão?
4. Isso é suficiente para especificar a aba `GLOSAS` do Excel final (colunas: percentual de ajuste, valor-base, valor da glosa) no spec.md, ou a informação genuinamente não existe ainda no Termo de Referência (nesse caso, reportar isso como a resposta — "fog externo ao repositório", não uma falha da pesquisa)?

Responder como resolução deste ticket: um resumo direto que permita escrever a seção do spec.md sobre glosa monetária, ou uma confirmação clara de que a informação não está disponível nos documentos do repositório e precisa ser obtida com o gestor do contrato.

## Answer

Pesquisa completa em `.scratch/inms-pipeline-spec/research/12-glosa-item-35.md`. O item 35 (identificado via as duas referências cruzadas em `06_modelo_de_execucao.html:1093` e `anexo_d_prazos.html:191`) corresponde à seção "Sanções Administrativas e Procedimentos para retenção ou glosa no pagamento" de `docs/termo_de_referencia/07_modelo_de_gestao.html` (linhas ~196-260 e ~893-1060).

1. **Fórmula**: `Ajuste_NMS(%) = Σ Pontos_NMS × 0,001` — 1 ponto de penalidade = 0,001% de glosa sobre o pagamento mensal (`07_modelo_de_gestao.html:218-221` e tabela em 936-961).
2. **Faixas/teto**: não há degraus — fórmula linear contínua. Há um teto de **30% do valor total mensal** (linhas 229-236); o excedente rola para a fatura do mês seguinte (exceto no último mês de vigência); ultrapassar o teto 3x em 6 meses caracteriza inexecução parcial do contrato (linhas 243-247).
3. **Agregação**: a pontuação é o **somatório de todos os `Pontos_NMS` do mês** (todos os 14 INMS, Anexos D e E combinados) — não é calculado por indicador e depois somado percentualmente; é soma de pontos primeiro, depois um único percentual (linhas 941-946).
4. **Suficiência para a aba GLOSAS**: sim, para o núcleo do cálculo — `percentual de ajuste = min(30%, Σ penalty_points × 0,001%)`, `valor da glosa = percentual × valor-base`. Ressalva documentada: uma segunda fórmula na mesma seção (linhas 965-1010) usa os termos `RB` e `Desconto Máximo Anual`, que **não são definidos em nenhum outro lugar do TR** — aparenta ser boilerplate de template genérico de contrato regulatório (rótulo "Anual" destoa do resto do item, que é inteiramente mensal) e não deve ser tratada como fonte de verdade operacional. Também fica ambíguo se "valor-base" é o valor total mensal do contrato ou por item/Ordem de Serviço (o texto usa ambos "pagamento mensal" e "PM_por_item"); recomenda-se assumir valor total mensal (é o termo usado explicitamente nas regras de teto) como convenção do spec.md, sem necessidade de esclarecimento externo — essa parte não bloqueia a especificação.
