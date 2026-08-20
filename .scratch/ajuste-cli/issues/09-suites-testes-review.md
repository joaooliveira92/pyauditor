# 09 - Suíte de testes dos cenários do review

Type: task
Status: open
Blocked by: 01, 02, 03, 04

## Question

Implementar os cenários de teste da seção **"Cenários de teste"** do `.scratch/ajuste-cli/review.md` como testes de regressão, agora que o contrato das decisões 01/02/03/04 travou (representação da glosa, criticidade, códigos de saída, resumo final).

Abrangência (do review):
- **Validação da capa**: capa inexistente; completa; competência ausente; competência divergente do argumento CLI; período fora da competência; período inicial > final; fiscais ausentes; valor mensal vazio/zero/negativo/formatado inválido.
- **Indicadores**: exatamente 14; ausente; duplicado; arquivo vazio; malformado; código interno divergente do arquivo; falha ao ler; valor não numérico; precisão decimal; processamento parcial.
- **Consolidação**: dois órgãos válidos; um válido + um incompleto; nenhum válido; relatório anterior inexistente; relatório anterior com decisões; preservação integral de decisões; conflito decisão anterior/nova; glosa calculável; glosa não calculável; **garantia de que não calculada nunca vira `0.00`** (ticket 01).
- **Operação**: idempotência; diretório sem permissão; arquivo Excel aberto/bloqueado; falha de escrita; escrita atômica; caminhos Windows e POSIX; interrupção durante consolidação; logs sem dados sensíveis.

Notes: os sintéticos já existentes cobrem parte; entregue como tickets de implementação nos arquivos de teste adequados; atenção à névoa "Validação de indicadores" (o "14" esperado ainda não foi decidido — não travar em 14 sem o ticket de validação).