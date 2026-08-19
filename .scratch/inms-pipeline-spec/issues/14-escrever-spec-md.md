Type: task
Status: resolved
Blocked by: 11, 12

## Question

Não há mais decisão de arquitetura de alto nível em aberto (tickets 01-10, 13 fecham a fronteira do grilling; tickets 11-12 preenchem os dois últimos blocos de fog conhecidos). Esta é uma tarefa de redação, não de decisão: consolidar as respostas de todos os tickets fechados deste mapa em um único `spec.md` na raiz do repositório (ou em `docs/spec/inms-pipeline.md`, a critério de quem executar), cobrindo:

- Visão geral e destino (ticket 01).
- Classificação dos 14 indicadores por shape, com a tabela final de 4 shapes (tickets 02, 13).
- Contratos Pydantic por shape, discriminated union (ticket 03).
- `QualityGateRunner` e a separação de duas camadas de validação (ticket 04).
- Estratégia de testes (ticket 05).
- Contrato da CLI (`bootstrap`/`measure`/`report`) (ticket 06).
- Contrato do ROM Markdown, com um exemplo renderizado por shape (ticket 07).
- Estrutura do repositório, dados de produção vs fixtures (ticket 08).
- Layout de pacotes e registry de strategies (ticket 09).
- Modelagem do campo `orgao` (ticket 10).
- Seção de INMS 1.8 (`external_catalog_sum`), preenchida com o achado do ticket 11.
- Seção de glosa monetária (aba `GLOSAS` do Excel final), preenchida com o achado do ticket 12 — ou, se o ticket 12 concluir que a informação não existe, documentar isso explicitamente como uma lacuna a resolver com o gestor do contrato antes da implementação, e não bloquear o resto da spec por isso.
- Contrato do Excel final e do Excel de capa, referenciando `docs/spreadsheet.md`/`docs/styleguide.md` e apontando o fog remanescente (mapeamento MinC/MTur, convenção de múltiplos ativos por indicador) como itens explicitamente fora do destino desta versão da spec.

## Answer

`spec.md` escrito em [`docs/spec/inms-pipeline.md`](../../../docs/spec/inms-pipeline.md), consolidando os 13 tickets fechados do mapa em 13 seções (visão geral, classificação de shapes, contratos Pydantic, validação em duas camadas, testes, CLI, contrato do ROM com exemplos renderizados para `ratio` e `external_catalog_sum`, layout de repositório/pacotes, campo `orgao`, INMS 1.8, glosa monetária, Excel final/capa). A seção final documenta explicitamente os 3 itens de fog remanescente (segregação MinC/MTur, schema de ingestão do INMS 1.8, convenção de múltiplos ativos por indicador) como fora do destino desta versão — nenhum bloqueia a implementação do escopo mono-órgão coberto pela spec.
