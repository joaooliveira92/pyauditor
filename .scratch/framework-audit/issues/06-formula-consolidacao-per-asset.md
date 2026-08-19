Type: research
Status: resolved

## Question

`docs/spreadsheet.md` diz que os indicadores de disponibilidade por ativo (INMS 1.4, 1.5, 1.14) não devem usar a fórmula padrão de consolidação MinC+MTur (`(Num MinC + Num MTur) / (Den MinC + Den MTur)`), e sim "a fórmula específica prevista no Termo de Referência" — nunca localizada em nenhuma fonte primária lida (`docs/spec/inms-pipeline.md` §"Fog remanescente", item 2). `orgao_consolidation.py` hoje deliberadamente deixa esses 3 indicadores sem consolidar (uma linha por órgão) para não arriscar aplicar a fórmula errada. Precisa reler o Termo de Referência (ou Anexo D) especificamente atrás dessa fórmula, ou confirmar com o gestor do contrato que ela não existe e a fórmula padrão deve valer também para esses 3.

## Answer

Não resolvido por pesquisa — a fórmula específica do Termo de Referência continua não localizada. Mas o mapa `multi-org-pipeline` fechou a decisão de escopo: por-ativo (1.4/1.5/1.14) fica **uma linha por órgão, sem consolidar**, até o TR definir a fórmula (registrado em "Out of scope" nesse mapa). `orgao_consolidation.py`/`consolidate.py` mantêm esse comportamento hoje. Reabrir apenas se surgir fonte primária nova (Anexo D ou confirmação do gestor do contrato) — até lá, fog deliberado, não pendência de implementação.
