Type: prototype
Status: open
Blocked by: 01

## Question

Subir a fidelidade do que o `consolidate` (2.1) produz: construir um **mock da planilha consolidada** (`reports/relatorio_<comp>_consolidado.xlsx` simulado) sobre os dados sintéticos MinC+MTur, para reagir.

Baseado no detalhe financeiro documentado no ticket [Mapear as abas financeiras da planilha de inspiração](01-inspiration-financial-tabs.md) e na fórmula decidida no ticket [Fórmula financeira da consolidação (2.1)](02-consolidation-formula.md):

- `INMS_BASE` consolidado (pooling Σnum/Σden, penalty = soma por órgão, 1.4/1.5/1.14 sem consolidar).
- `GLOSAS`: linhas por (indicador×órgão) + resumo; `Total de Pontos` derivado; colunas de **decisão** vagas (Justificativa/Decisão Fiscal) para o fiscal preencher — sugestão de glosa, com anistia possível.
- `CALCULO_PAGAMENTO`: colunas MinC/MTur/Consolidado com rateio 0.5/0.5 e glosa na coluna consolidada.
- `SERVICOS_POR_ORGAO`: matriz 9 serviços, flags MinC/MTur/segregação.
- `CAPA_E_CONTROLE` com valor mensal e valor global anual.

## Answer

(aberto)