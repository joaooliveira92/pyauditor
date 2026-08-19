Type: research
Status: resolved

## Question

INMS 1.8 ("Ocorrências de Desconformidade Técnica") usa o shape `external_catalog_sum`: soma de pontos de desconformidade técnica catalogados no Anexo E, sem meta percentual, penalidade "conforme Anexo E" (Tabela 28 do Anexo D não detalha os valores). Ler `/Users/joao/dev/pyauditor/docs/termo_de_referencia/anexo_e_desconformidade_tecnica.html` e responder:

1. Qual a estrutura do catálogo de desconformidades (categorias, código de cada ocorrência, pontuação por ocorrência)?
2. Como uma ocorrência de desconformidade é registrada/identificada no dataset de origem (existe um CSV esperado para INMS 1.8, e qual o formato — o `input/inms-001-08.csv` real está vazio, só header: `Nº Solicitacao ; Contrato ; Atividades ; SLA ; Tipo Demanda ; DataHoraSolicitacao ; DataHoraLimite ; DataHoraFim ; No prazo ; Grupo_executor ; solicitante ; Criador ; TecnicoExecutor` — isso bate com o Anexo E, ou o formato real esperado é outro?)?
3. Existe reincidência/multiplicador de pontuação, teto de pontuação mensal, ou é soma linear simples?
4. Isso é suficiente para especificar o `calculation`/`penalty` Pydantic model do shape `external_catalog_sum` no spec.md final, ou falta alguma referência cruzada (ex: outro anexo)?

Responder como resolução deste ticket: um resumo direto (não precisa ser exaustivo linha a linha do Anexo E) que permita escrever a seção do spec.md para INMS 1.8 sem re-ler o HTML.

## Answer

Pesquisa completa em `docs/research/anexo-e-inms-1.8.md` (leitura integral do HTML, ~2714 linhas). Resumo:

1. **Estrutura do catálogo**: Anexo E é uma única tabela, Tabela 29 "Itens de Desconformidade Técnica", com 106 itens (`OD-01`..`OD-106`) em 22 categorias (ASSUNTO). Colunas: ID, ASSUNTO, DESCRIÇÃO, REFERÊNCIA (unidade de contagem), PONTUAÇÃO. Pontuação varia de 50 a 20.000 pontos por item (ex.: OD-01 "perder dados críticos" = 20.000; OD-52 "cabo de rede solto" = 100). A REFERÊNCIA não é uniformemente "por ocorrência": também existem "por dia de atraso", "por solução", "por Item de Configuração", "por produto", "por evento" — a unidade de contagem é específica de cada item do catálogo, não uma tally única.

2. **Formato do dataset de origem**: Anexo E **não define nenhum mecanismo de coleta/registro** — é puramente um catálogo/tabela de preços (código → descrição → pontos), sem menção a sistema, formulário ou processo de auditoria. Conclusão: o formato ITSM (`inms-001-08.csv`, mesmo header de tickets de chamado) é um formato plausível mas **não confirmado**, e há incompatibilidades estruturais reais — vários itens do catálogo (cabo solto, vestimenta inadequada, ausência de pentest, desatualização de CMDB) são achados de inspeção/auditoria, não eventos de chamado de ticket. O campo `Atividades` (texto livre) é o único candidato a carregar um código `OD-NN`, mas nada no Anexo E ou D sugere esse mapeamento. O fato de os arquivos irmãos `inms-001-03/09/10.csv` (indicadores `ratio` de fato) compartilharem o mesmo header vazio sugere que o header compartilhado é artefato da ferramenta de exportação ITSM usada para todos os indicadores, não evidência de que esse é o formato correto para 1.8. **Isso fica genuinamente indeterminado pelas fontes primárias** — recomenda-se tratar como pergunta em aberto para a equipe de fiscalização, não assumir o CSV atual como autoritativo.

3. **Reincidência/teto**: Não há teto mensal de pontuação e não há multiplicador por reincidência — cada item tem pontuação fixa, mesmo repetido. A única regra de ajuste é "se uma ocorrência se enquadra em mais de um item, conta apenas o de maior pontuação" (dedup por ocorrência, não por período). A fórmula do Anexo D é soma linear simples: `INMS 1.8 = ΣPDT`, sem cap.

4. **Suficiência para o modelo Pydantic**: Anexo E + Tabela 28 (Anexo D) são suficientes para modelar o **catálogo** (id, categoria, descrição, unidade, pontos) e o **cálculo bruto** (soma dos pontos dos itens correspondentes, com a regra de maior-pontuação-vence). **Não são suficientes** para o modelo completo de `calculation`/`penalty`, por dois motivos: (a) a conversão pontos→glosa monetária está fora do Anexo E — Anexo D remete explicitamente ao item 35 do Termo de Referência, já rastreado (e ainda não resolvido) no ticket 12; (b) o próprio mecanismo de registro/ingestão de uma ocorrência (que schema um "registro de origem" precisa ter) não é definido em nenhuma fonte primária lida até agora. Para o `spec.md`, isso significa: o shape `external_catalog_sum` pode ser especificado com um catálogo Pydantic fixo (106 itens, carregado de um arquivo próprio do YAML/config, não do Anexo D) e uma função de soma, mas o "dataset schema" de entrada para INMS 1.8 continua fog — não deve ser assumido como o formato ITSM genérico sem confirmação operacional.

Pesquisa completa: [`docs/research/anexo-e-inms-1.8.md`](../../../docs/research/anexo-e-inms-1.8.md).
