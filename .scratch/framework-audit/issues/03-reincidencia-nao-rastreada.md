Type: research
Status: resolved

## Question

`docs/spreadsheet.md` §Aba 10 (`GLOSAS`) lista uma coluna "reincidência" nas colunas propostas, mas nada no pipeline atual sabe se um indicador já descumpriu a meta em competências anteriores. O Termo de Referência prevê agravamento de penalidade por reincidência (ex.: um multiplicador, ou uma faixa de glosa diferente no 2º/3º mês consecutivo de não conformidade para o mesmo indicador)? Se sim, isso é outro caso de estado entre competências (ver [[02-rollover-glosa-nao-consumido]]) que o pipeline stateless atual não tem como resolver sem uma fonte de histórico.

## Answer

**O TR prevê agravamento, mas não é um multiplicador de glosa — é um gatilho de sanção administrativa separada.** Texto literal (`07_modelo_de_gestao.html:243-247`, citado em `.scratch/inms-pipeline-spec/research/12-glosa-item-35.md` §2):

> "Caso o percentual de glosa ultrapasse o limite acima de 03 (três) vezes em um período de 06 (seis) meses, será caracterizada **INEXECUÇÃO PARCIAL DO CONTRATO**, sujeitando a CONTRATADA às sanções cabíveis."

Ou seja: reincidência aqui não muda a fórmula de conversão pontos→glosa nem cria uma faixa diferente de glosa no 2º/3º mês — o cálculo monetário (`Σ Pontos × 0,001%`, teto 30%) é sempre o mesmo. O que existe é um contador de "quantas vezes o teto de 30% foi estourado nos últimos 6 meses"; ao atingir 3, o evento vira inexecução parcial contratual (fora do escopo do cálculo de glosa em si — aciona outras sanções). A coluna "reincidência" da aba `GLOSAS` (`docs/spreadsheet.md` §Aba 10) deve ser esse contador/flag de compliance, não uma variável monetária.

Continua precisando de estado entre competências para contar as ocorrências — mesma família de [[02-rollover-glosa-nao-consumido]]. Ticket de acompanhamento: [[11-estado-persistente-entre-competencias]].
