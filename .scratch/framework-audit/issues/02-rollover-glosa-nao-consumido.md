Type: research
Status: resolved

## Question

`compute_glosa` (`src/pyauditor/excel/glosas.py`) calcula `saldo_rolado_pct` quando o teto de 30% é atingido, mas nada lê esse valor de volta no `report` do mês seguinte — é só informativo na aba `GLOSAS`. O item 35 do Termo de Referência (`docs/termo_de_referencia/07_modelo_de_gestao.html`, já citado em `docs/research/12-glosa-item-35.md`) realmente exige que o excedente acima do teto componha o cálculo do mês seguinte, ou o teto de 30% é um limite duro por competência sem efeito cascata? Se exige, o pipeline precisa de estado entre execuções de `report` (hoje cada run é stateless).

## Answer

**Exige, sim — é um requisito real do TR, não um teto duro sem efeito cascata.** Texto literal (`07_modelo_de_gestao.html:229-236`, citado em `.scratch/inms-pipeline-spec/research/12-glosa-item-35.md` §2):

> "A glosa sobre o pagamento mensal será aplicada até o limite de 30% do valor total mensal... Caso o saldo devedor ultrapasse o limite de 30% de glosa estabelecido, **o restante poderá ser aplicado na fatura do mês subsequente**, com a exceção do último mês de vigência do contrato."

`compute_glosa` (`src/pyauditor/excel/glosas.py`) já calcula `saldo_rolado_pct` corretamente, mas confirmado por leitura do código atual: nada em `report`/`cli` lê esse valor de volta no mês seguinte — cada execução continua stateless. É um gap real de implementação, não uma leitura equivocada da spec. Abre ticket de acompanhamento: [[11-estado-persistente-entre-competencias]] (decisão de prioridade de implementação, junta com [[03-reincidencia-nao-rastreada]] e a conclusão negativa de [[04-teto-anual-glosa]] — mesma família de "pipeline precisa de histórico entre execuções mensais").
