Type: research
Status: open

## Question

`docs/spreadsheet.md` diz que os indicadores de disponibilidade por ativo (INMS 1.4, 1.5, 1.14) não devem usar a fórmula padrão de consolidação MinC+MTur (`(Num MinC + Num MTur) / (Den MinC + Den MTur)`), e sim "a fórmula específica prevista no Termo de Referência" — nunca localizada em nenhuma fonte primária lida (`docs/spec/inms-pipeline.md` §"Fog remanescente", item 2). `orgao_consolidation.py` hoje deliberadamente deixa esses 3 indicadores sem consolidar (uma linha por órgão) para não arriscar aplicar a fórmula errada. Precisa reler o Termo de Referência (ou Anexo D) especificamente atrás dessa fórmula, ou confirmar com o gestor do contrato que ela não existe e a fórmula padrão deve valer também para esses 3.

## Answer

(aberto)
