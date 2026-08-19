# pyauditor — documentação

O `pyauditor` apura mensalmente os **14 indicadores INMS** de SLA do contrato
40/2022 (Ministério da Cultura, Anexo D) a partir de pares declarativos
`inms-<n>.yaml` + `inms-<n>.csv`. Para cada indicador ele roda gates de
qualidade, calcula a medição por um de cinco *shapes*, escreve um ROM (memória
de cálculo) em Markdown e consolida tudo em uma planilha Excel final, com capa
do contrato e aba de glosas.

Para a especificação arquitetural completa, veja
[`docs/spec/inms-pipeline.md` no repositório](https://github.com/joaooliveira92/pyauditor/blob/master/docs/spec/inms-pipeline.md).

## Mapa do portal

- [Começando](getting-started/index.md) — instale, rode sua primeira competência.
- [Conceitos](concepts/index.md) — como o pipeline funciona: arquitetura, shapes e organização de dados.
- [Referência](reference/index.md) — CLI, schema de config, formato do ROM/JSON e abas do Excel.
- [Guias de operação](guides/index.md) — capa, medição, relatório final e novos indicadores.
- [Operações e troubleshooting](operations/troubleshooting.md) — falhas conhecidas e recuperação.
- [Glossário](glossary.md) — vocabulário do domínio.

> **Nota de privacidade:** os dados de produção (`input/`) não são versionados —
> os CSVs reais contêm PII (nome, solicitante, técnico). Veja
> [conceitos de dados](concepts/data-layout.md).