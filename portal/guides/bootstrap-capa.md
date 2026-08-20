# Crie a capa do contrato

Use este procedimento para criar (uma vez) e depois preencher a capa usada pelo
`report`.

## Pré-requisitos

- Projeto instalado ([Instalação](../getting-started/installation.md)).

## Procedimento

1. Crie a capa do órgão (idempotente — não sobrescreve se já existir):

   ```bash
   uv run pyauditor bootstrap --orgao MinC --capa-path capa_MinC.xlsx
   ```

   Por default, `bootstrap` cria `capa_<orgao>.xlsx` (use `--orgao MTur` para
   `capa_MTur.xlsx`; `--orgao both` cria ambas). `--capa-path` permite um
   caminho próprio.

2. Abra `capa_MinC.xlsx` (o `--orgao` correspondente) e preencha o campo
   **Valor mensal vigente** (necessário para o valor da glosa). Os demais
   campos da aba `CAPA_E_CONTROLE` são de preenchimento do fiscal.

## Verificação

- O arquivo existe em `capa_<orgao>.xlsx`.
- A aba `CAPA_E_CONTROLE` lista os campos do contrato com a célula
  «Situação geral da aferição» preenchida.

## Observações

- Rodar `bootstrap` de novo **não** recria a capa existente — é intencional
  para evitar que o fiscal perca dados preenchidos.
- O `report` reaproveita a capa do órgão (embedded na primeira aba do
  relatório), sem duplicar conteúdo, ver [Planilha Excel](../reference/excel.md).

## Próximos passos

- [Medir uma competência](measure-indicators.md)