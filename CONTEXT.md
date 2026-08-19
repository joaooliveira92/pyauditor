# pyauditor

Pipeline de aferição do contrato 40/2022 (MinC/MTur): mede indicadores INMS 1.1–1.14 por competência e gera o workbook mensal de aferição financeira.

## Language

**Órgão**:
Cada entidade contratante coberta pelo relatório (MinC, MTur). Cada órgão tem configs, inputs e outputs próprios; a consolidação os funde apenas no passo `consolidate`.
_Avoid_: cliente, contratante

**Competência**: O mês de aferição, escrito `YYYY-MM`. Dá nome aos inputs e outputs mensais.

**Glosa**: Dedução aplicada sobre o valor mensal vigente quando indicadores não cumprem a meta. Nunca é silenciosa: nasce de uma não-conformidade registrada e termina numa decisão do fiscal.
_Avoid_: desconto, multa, penalidade

**Sugestão de glosa**: O que o pipeline calcula automaticamente: linhas de não-conformidade (indicador×órgão) com `%Ajuste` e `Valor Glosa` propostos e colunas de decisão vazias. É proposta, não sentença.

**Glosa por ocorrência**: O `Valor Glosa` de uma linha específica (indicador × órgão) = `Valor Base × %Ajuste/100`. Compõe o agregado, mas não é a glosa final.

**Glosa da competência**: A dedução final aplicada ao pagamento do mês = `MIN(Total de Pontos × 0.001, 30%) × valor mensal`, sobre as ocorrências não-anistadas.

**Anistia**: Decisão do fiscal de aceitar a justificativa do fornecedor para uma não-conformidade, tirando a ocorrência da base da glosa da competência (`%Ajuste` zera na linha).
_Avoid_: perdoar, dispensar

**Decisão fiscal**: O aceitar/não-aceitar do fiscal registrado na planilha consolidada, por ocorrência. Decide se cada glosa sugerida permanece.

**Rateio MinC/MTur**: Parâmetro fiscal (hoje provisório 0.5/0.5) que divide o pagamento entre os dois órgãos. Entrada do fiscal, não calculada pelo pipeline.
_Avoid_: proporção, divisão