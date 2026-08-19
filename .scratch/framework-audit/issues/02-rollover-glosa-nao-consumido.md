Type: research
Status: open

## Question

`compute_glosa` (`src/pyauditor/excel/glosas.py`) calcula `saldo_rolado_pct` quando o teto de 30% é atingido, mas nada lê esse valor de volta no `report` do mês seguinte — é só informativo na aba `GLOSAS`. O item 35 do Termo de Referência (`docs/termo_de_referencia/07_modelo_de_gestao.html`, já citado em `docs/research/12-glosa-item-35.md`) realmente exige que o excedente acima do teto componha o cálculo do mês seguinte, ou o teto de 30% é um limite duro por competência sem efeito cascata? Se exige, o pipeline precisa de estado entre execuções de `report` (hoje cada run é stateless).

## Answer

(aberto)
