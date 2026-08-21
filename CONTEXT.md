# pyauditor

Pipeline de aferição do contrato 40/2022 (MinC/MTur): mede indicadores INMS 1.1–1.14 por competência e gera o workbook mensal de aferição financeira.

## Language

**Órgão**:
Cada entidade contratante coberta pelo relatório (MinC, MTur). Cada órgão tem configs, inputs e outputs próprios; a consolidação os funde apenas no passo `consolidate`.
_Avoid_: cliente, contratante

**Competência**: O mês de aferição, escrito `YYYY-MM`. Dá nome aos inputs e outputs mensais. Informada obrigatoriamente na CLI; deriva o Período de aferição.

**Período de aferição**: Intervalo de datas da competência, do primeiro ao último dia do mês. Derivado da competência informada na CLI — nunca lido da capa nem inferido dos dados. Delimita quais linhas do dataset pertencem à aferição.
_Avoid_: período da capa, datas da planilha

**Equipe**: Quadro de responsáveis do contrato (gestão e fiscalização), com função, nome e SIAPE. Fonte dos campos de responsáveis da planilha; substitutos ficam registrados na Equipe, fora da capa.
_Avoid_: responsáveis da capa

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

**ROM**: Relatório de Ocorrências e Medição — o markdown por indicador×competência (ou indicador×categoria×competência, para INMS segmentados por Categoria) que documenta a memória de cálculo de uma medição. Insumo para a Glosa por ocorrência, não a decisão em si.

**Pontuação apurada**: Os pontos de INMS/IMR calculados pela regra contratual do indicador (base + degraus abaixo da meta). Entra como insumo em `%Ajuste`/Glosa por ocorrência; não é, por si só, sanção administrativa.
_Avoid_: penalidade, multa, sanção

**Ressalva interpretativa**: Nota no ROM que declara quando uma regra contratual admite mais de uma leitura plausível (ex.: degraus lineares vs. degraus inteiros) e mostra os resultados de cada leitura, sem o pipeline decidir qual prevalece.

**Linhas aprovadas pelo quality gate**: As linhas do CSV que passaram nos `quality_gates` do indicador. Não equivale a população contratual (ex.: um incidente sem `DataHoraFim` pode ser rejeitado pelo gate mas ainda pertencer à população de incidentes abertos no período) — distinção que o ROM precisa declarar, não apenas o pipeline.
_Avoid_: população, linhas aceitas (sem qualificação)

**Grupo executor**: Coluna já existente no CSV bruto do fornecedor, identificando qual equipe atendeu o incidente (ex.: `(CIT/MINC) - 2º Nível`, `(CIT/MINC) - 2º Nível/RJ`, `Executores CODIN/SEI`). Fonte de verdade para derivar a Categoria; não é escrita nem inferida pelo pipeline.

**Categoria**: Agrupamento de negócio de um INMS (ex.: "Atendimento Remoto aos Usuários") definido por um filtro sobre Grupo executor. Um INMS pode pertencer a mais de uma categoria, e o subconjunto de categorias válidas varia por INMS — não é fixo para todos os indicadores. Cada categoria de um INMS gera uma medição independente (seu próprio ROM), sobre o mesmo shape de cálculo e a mesma meta do Anexo D do indicador — o que muda é o subconjunto de linhas de entrada, não o contrato do indicador. Quando o INMS também é medido por Ativo (ex.: INMS 1.14), Categoria e Ativo compõem: cada Ativo gera uma medição independente sob cada Categoria à qual o INMS pertence.

**Ativo**: Um dos serviços de infraestrutura nomeados no Anexo D de um INMS medido "por ativo" (ex.: INMS 1.14: File Server, Telefonia, Mensageria, Servidores de impressão, WI-FI, Rede). Cada Ativo tem seu próprio par YAML+CSV e gera uma medição independente (seu próprio ROM), com o mesmo `contractual_id` do indicador. Dimensão de segmentação distinta de Categoria: Ativo nomeia um serviço de infraestrutura monitorado, Categoria filtra por Grupo executor — não se sobrepõem, mas compõem quando ambas se aplicam ao mesmo INMS.
_Avoid_: serviço (sem qualificação — ambíguo com "serviço de atendimento")

**Categoria "outros"**: Categoria catch-all contábil de um INMS: captura as linhas cujo Grupo executor não bate com nenhuma categoria substantiva do indicador. É contada mas não entra no cálculo de conformidade/meta — existe só para que nenhuma linha do dataset do fornecedor desapareça sem explicação.
_Avoid_: linhas rejeitadas, fora de escopo (essas linhas não falharam quality gate — só não pertencem a nenhuma categoria substantiva)