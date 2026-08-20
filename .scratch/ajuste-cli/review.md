# Map: pyauditor — cli review

Label: wayfinder:map

Avaliação geral
Diagnóstico resumido

O pipeline aparenta ter executado todas as etapas:

identificou as capas existentes;
avaliou campos obrigatórios ou esperados;
apurou 14 indicadores para cada órgão;
gerou dois relatórios individuais;
gerou um consolidado;
exibiu um resumo operacional.

Contudo, eu classificaria o resultado como:

Execução concluída com pendências críticas de dados, não como execução plenamente bem-sucedida.

O principal problema é semântico: o output mostra glosa: 0.00, mas também informa que o valor mensal não foi preenchido e, por isso, o valor da glosa não pôde ser calculado. Numericamente, zero e não calculado são estados diferentes.

Principais achados

1. Alta prioridade: glosa: 0.00 pode transmitir informação incorreta

O log informa:

capa sem 'Valor mensal vigente' preenchido — GLOSAS terá percentual de ajuste mas não valor da glosa

Depois apresenta:

relatório consolidado: ... (total de pontos: 46909.85, glosa: 0.00)

Isso cria uma ambiguidade perigosa:

0.00 pode significar que a glosa foi calculada e não houve desconto;
mas, pelo aviso anterior, aparentemente significa que o cálculo monetário não pôde ser realizado.
Sugestão

Representar explicitamente o estado:

glosa: não calculada

ou:

glosa: indisponível — Valor mensal vigente não informado

Se o artefato Excel exigir uma célula numérica, é preferível deixá-la vazia e criar outra célula com o status do cálculo. Não recomendo preencher com zero.

Questionamentos
O consolidado usa 0.00 como valor padrão quando o valor mensal está ausente?
Existe uma propriedade interna como glosa_calculada, valor_disponivel ou calculation_status?
Uma glosa monetária não calculada pode ser confundida com ausência efetiva de glosa?
Os sistemas ou usuários posteriores somam esse 0.00 como se fosse um resultado válido?
O percentual de ajuste calculado aparece claramente nos relatórios? 2. Alta prioridade: não está claro se os campos ausentes impedem a validade do relatório

Para MinC:

Competência, Fiscal administrativo

Para MTur:

Competência, Período inicial da aferição, Período final da aferição,
Fiscal técnico, Fiscal requisitante, Fiscal administrativo,
Gestor do contrato

No MTur, a quantidade de campos ausentes é expressiva. Mesmo assim, o processo segue normalmente e produz o relatório.

É necessário distinguir pelo menos três categorias:

obrigatório para processar;
obrigatório para publicar ou assinar;
opcional.

Hoje todos os casos parecem virar apenas WARNING, sem explicar o impacto.

Sugestão

Adicionar a criticidade e o efeito de cada ausência:

WARNING | Dados incompletos | órgão=MTur
Campos obrigatórios para publicação: Competência, Período inicial, Período final
Campos administrativos pendentes: Fiscal técnico, Fiscal requisitante,
Fiscal administrativo, Gestor do contrato
Impacto: relatório gerado como rascunho; não está pronto para publicação

Se Competência é derivada do argumento 2026-06, vale questionar por que ela permanece sem preenchimento na capa.

Questionamentos
A competência deveria ser automaticamente preenchida a partir de pyauditor run 2026-06?
Os períodos inicial e final também podem ser derivados da competência?
Esses campos são obrigatórios por regra contratual ou apenas informativos?
O relatório sem os fiscais e o gestor identificados pode ser considerado formalmente válido?
O arquivo gerado recebe alguma marcação de RASCUNHO, INCOMPLETO ou NÃO PUBLICÁVEL?
O comando deveria retornar código diferente de zero quando campos obrigatórios estão ausentes? 3. Média prioridade: “capa já existe, nada a fazer” não descreve completamente o comportamento

O log diz:

capa já existe, nada a fazer: capa_MinC.xlsx

Logo depois, a capa é lida e validada.

Portanto, “nada a fazer” é impreciso. O sistema não recriou a capa, mas ainda a utilizou no processamento.

Sugestão

Usar uma mensagem mais objetiva:

capa existente será reutilizada: capa_MinC.xlsx

ou:

bootstrap ignorado: capa já existe e será validada

Também seria útil indicar se o arquivo foi:

apenas encontrado;
validado;
modificado;
preservado integralmente;
usado como entrada. 4. Média prioridade: a execução não apresenta um status final inequívoco

O resumo mostra as etapas, mas não há mensagem como:

Execução concluída com avisos

Também não aparecem:

código de saída;
quantidade total de avisos;
quantidade de erros;
duração;
status de validade dos artefatos;
indicação de que a publicação está bloqueada ou liberada.
Sugestão de resumo final
Resultado: CONCLUÍDO COM PENDÊNCIAS
Competência: 2026-06
Órgãos processados: 2
Indicadores apurados: 28
Relatórios individuais: 2
Relatórios consolidados: 1
Avisos: 4
Erros: 0
Glosa monetária: não calculada
Publicação: não recomendada até o preenchimento das capas
Duração: 1,24 s

Esse resumo permitiria que uma pessoa determinasse imediatamente se precisa realizar alguma ação.

5. Média prioridade: os logs dos indicadores são pouco informativos

Cada indicador aparece desta forma:

INMS 1.1: roms\MinC\2026-06\INMS-01.md

Não fica claro se isso significa:

arquivo localizado;
arquivo validado;
indicador processado;
apuração concluída;
resultado extraído;
ROM gerada;
ROM apenas usada como entrada.
Sugestão

Use um verbo ou evento que represente o fato:

indicador apurado: código=INMS-1.1 rom=roms\MinC\2026-06\INMS-01.md

Idealmente, inclua o resultado essencial:

indicador apurado: órgão=MinC código=INMS-1.1 pontos=... status=conforme

Se há informações sensíveis, registre apenas os dados operacionais mínimos necessários.

Questionamentos
Esses arquivos foram criados, lidos ou atualizados?
Um arquivo ausente interrompe o processo?
Um arquivo vazio ou malformado é detectado?
O número de indicadores esperado é sempre 14?
Uma execução com 13 indicadores ainda gera relatório?
Há validação contra duplicidade de códigos? 6. Média prioridade: 0 decisão(ões) preservada(s) é ambíguo

O resumo exibe:

(0 decisão(ões) preservada(s))

Isso pode significar:

não havia decisões anteriores;
havia decisões, mas nenhuma foi preservada;
a preservação não foi necessária;
o mecanismo não encontrou uma versão anterior;
houve falha silenciosa na detecção.
Sugestão

Explicitar o denominador ou o motivo:

decisões anteriores encontradas=0 preservadas=0

ou:

nenhuma decisão anterior encontrada para preservação

Questionamentos
O que exatamente é uma “decisão”?
Onde essas decisões ficam armazenadas?
A preservação ocorre ao sobrescrever um consolidado existente?
Se havia decisões e nenhuma foi preservada, isso seria erro?
Existe teste de regressão garantindo que decisões manuais não sejam perdidas? 7. Baixa prioridade: portabilidade e exibição dos caminhos

Os caminhos estão no formato Windows:

roms\MinC\2026-06\INMS-01.md

Isso pode ser adequado ao ambiente atual, mas vale verificar se a CLI precisa funcionar em Linux, CI ou containers.

Além disso, o resumo corta o caminho:

reports\relatorio_2026-06_consolidado.xl…

A interface resumida está bonita, mas o truncamento dificulta copiar o caminho final.

Sugestões
Gerar caminhos com pathlib.
Manter a apresentação nativa do sistema operacional.
Exibir o caminho completo após a tabela.
Considerar um modo --no-truncate.
Oferecer saída estruturada para automação, como --output json. 8. Baixa prioridade: padronização numérica e contexto dos pontos

O resultado apresenta:

total de pontos: 46909.85

Para uma saída voltada a usuários brasileiros, poderia ser:

46.909,85

Para logs estruturados ou consumo por máquinas, o ponto decimal está correto. O ideal é separar os casos:

logging técnico: 46909.85;
apresentação humana: 46.909,85.

Também falta contexto sobre o número:

é a soma dos dois órgãos?
qual foi o total de cada órgão?
qual é a unidade?
existe máximo esperado?
valores muito altos ou baixos são validados?
Sugestões de melhoria por prioridade
Prioridade 1: preservar a semântica do resultado
Não representar glosa indisponível como 0.00.
Separar:
percentual de ajuste;
valor monetário da glosa;
status do cálculo;
motivo da indisponibilidade.
Marcar relatórios incompletos como rascunho.
Definir quais pendências bloqueiam publicação.
Evitar que uma execução incompleta pareça plenamente bem-sucedida.
Prioridade 2: tornar o resumo acionável

Adicionar ao final:

status global;
total de warnings e erros;
pendências por órgão;
glosa calculada ou não calculada;
qualidade/publicabilidade dos artefatos;
duração;
código de saída;
caminhos finais sem truncamento.
Prioridade 3: melhorar observabilidade

Adicionar contexto estável aos eventos:

event=indicator_measured
orgao=MinC
competencia=2026-06
indicator=INMS-1.1
rom_path=...
status=success
duration_ms=...

Não é necessário trocar imediatamente o formato visual. A CLI pode continuar amigável e, opcionalmente, oferecer logs JSON com --log-format json.

Prioridade 4: reduzir ruído

Há 28 linhas praticamente idênticas dos indicadores. Para uso interativo, poderia haver uma saída concisa:

MinC: 14/14 indicadores apurados
MTur: 14/14 indicadores apurados

E os detalhes poderiam ficar disponíveis com --verbose.

Uma política razoável:

padrão: etapas, pendências e resumo;
-v: um evento por indicador;
-vv: detalhes de leitura, validação e cálculo;
JSON: todos os eventos estruturados.
Comportamento sugerido para o código de saída

Uma convenção possível:

0: execução concluída e artefatos válidos;
1: falha técnica ou artefato não gerado;
2: uso inválido da CLI;
3: execução concluída, mas dados obrigatórios estão incompletos;
4: relatório gerado, porém cálculo financeiro indisponível.

Se códigos distintos forem excessivos para o projeto, pelo menos use:

0: válido;
1: erro;
2: concluído com pendência impeditiva.

Isso é especialmente importante para CI, workers e automações.

Cenários de teste que eu recomendaria
Validação da capa
capa inexistente;
capa existente e completa;
competência ausente;
competência divergente do argumento da CLI;
período fora da competência;
período inicial posterior ao final;
fiscais ausentes;
valor mensal vazio;
valor mensal zero;
valor mensal negativo;
valor mensal em formato inválido.
Indicadores
exatamente 14 indicadores;
indicador ausente;
indicador duplicado;
arquivo vazio;
Markdown malformado;
código interno divergente do nome do arquivo;
falha ao ler um dos arquivos;
valor não numérico;
soma com precisão decimal;
processamento parcial.
Consolidação
dois órgãos válidos;
um válido e outro incompleto;
nenhum válido;
relatório anterior inexistente;
relatório anterior com decisões;
preservação integral das decisões;
conflito entre decisão anterior e nova apuração;
glosa calculável;
glosa não calculável;
garantia de que não calculada nunca vire zero.
Operação
execução repetida e idempotente;
diretório sem permissão;
arquivo Excel aberto ou bloqueado;
falha durante escrita;
escrita atômica para evitar arquivo parcialmente produzido;
caminhos Windows e POSIX;
interrupção durante consolidação;
logs sem dados sensíveis.
Perguntas que eu levaria para a equipe
Sobre regras de negócio
O relatório pode ser oficialmente emitido sem competência?
A competência da capa deve necessariamente coincidir com 2026-06?
Os períodos podem ser derivados automaticamente?
Quais papéis são obrigatórios antes da publicação?
O percentual de ajuste é válido mesmo sem o valor mensal?
O valor de glosa ausente deve aparecer vazio, indisponível ou pendente?
O total de pontos é informativo ou influencia diretamente a glosa?
Qual é a precisão financeira exigida e o projeto usa Decimal?
Sobre processamento
O pipeline é transacional por órgão ou para a execução inteira?
Uma falha no MTur deveria impedir o relatório do MinC?
Os relatórios são escritos atomicamente?
Uma execução repetida produz resultados idênticos?
As capas são somente entradas ou também são atualizadas?
Como se detecta que uma capa pertence à competência correta?
Os 14 indicadores são fixos ou configuráveis?
Sobre preservação
O que são as decisões preservadas?
Como se identifica uma decisão manual?
Existe risco de sobrescrever edição humana?
O sistema mantém backup antes de atualizar o consolidado?
Há trilha de auditoria mostrando o que foi preservado?
Exemplo de output mais claro
11:39:38 | INFO | execução iniciada | competência=2026-06 órgãos=MinC,MTur
11:39:38 | INFO | capa existente reutilizada | órgão=MinC arquivo=capa_MinC.xlsx
11:39:38 | WARNING | capa incompleta | órgão=MinC campos=Competência,Fiscal administrativo
11:39:38 | INFO | apuração concluída | órgão=MinC indicadores=14/14
11:39:39 | INFO | capa existente reutilizada | órgão=MTur arquivo=capa_MTur.xlsx
11:39:39 | WARNING | capa incompleta | órgão=MTur campos=Competência,Período inicial,...
11:39:39 | INFO | apuração concluída | órgão=MTur indicadores=14/14
11:39:39 | WARNING | glosa monetária não calculada | órgão=MinC motivo=valor mensal ausente
11:39:39 | WARNING | glosa monetária não calculada | órgão=MTur motivo=valor mensal ausente
11:39:39 | INFO | relatório gerado | órgão=MinC caminho=reports\relatorio_2026-06_MinC.xlsx
11:39:39 | INFO | relatório gerado | órgão=MTur caminho=reports\relatorio_2026-06_MTur.xlsx
11:39:39 | INFO | consolidado gerado | caminho=reports\relatorio_2026-06_consolidado.xlsx

Resultado: CONCLUÍDO COM PENDÊNCIAS
Indicadores: 28/28
Avisos: 4
Erros: 0
Total de pontos: 46.909,85
Percentual de ajuste: disponível
Valor monetário da glosa: NÃO CALCULADO
Publicação: BLOQUEADA até o preenchimento dos campos obrigatórios

Conclusão

O output demonstra um fluxo organizado e rápido, com boa identificação dos artefatos e separação por órgão. Porém, antes de considerá-lo adequado para produção, eu trataria três pontos:

não exibir glosa zero quando ela não foi calculada;
deixar explícito o impacto dos campos não preenchidos;
encerrar com um status global inequívoco e acionável.

O risco mais relevante não parece ser uma falha técnica, mas um resultado incompleto ser interpretado como resultado financeiro válido.

Melhorias aplicadas na análise
Separei problemas de corretude, observabilidade e experiência da CLI.
Diferenciei ausência de valor de um resultado legítimo igual a zero.
Transformei mensagens ambíguas em sugestões operacionais e critérios testáveis.
Priorizei questionamentos que ajudam a definir contratos, códigos de saída e validade dos relatórios.
