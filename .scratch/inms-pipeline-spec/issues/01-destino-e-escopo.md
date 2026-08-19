Type: grilling
Status: resolved

## Question

Qual é o artefato final que encerra o mapa "pyauditor — spec do pipeline de apuração INMS" — um `spec.md` de arquitetura para outra sessão implementar, ou código funcionando? Os 14 indicadores INMS entram todos como decisão de design agora, ou o destino é um engine genérico provado por 1 indicador de referência? A planilha Excel final e o Excel de capa do contrato entram no mesmo mapa?

## Answer

- Destino = `spec.md` (arquitetura + contratos de módulo + decisões travadas), não implementação. Volume de decisões (modelagem YAML, engine vs codegen, estrutura de módulos, contrato do ROM, contrato do Excel) justifica travar tudo antes de codar.
- Escopo dos 14 indicadores = engine genérico o bastante para qualquer YAML aderente ao schema; os indicadores que não divergem estruturalmente do INMS 1.1 não exigem decisão nova, só configuração (ver ticket 02 para a classificação real, obtida lendo o Anexo D).
- A planilha Excel final consolidada e o Excel de capa do contrato entram no mesmo mapa — a CLI já precisa gerenciar a capa desde o início (bootstrap), e o Excel final é o destino declarado pelo usuário; não faz sentido fatiar em dois mapas para um fluxo único ROM→Excel.
