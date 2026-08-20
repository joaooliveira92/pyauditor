Type: prototype
Status: resolved
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

Mock gerado e aprovado pelo fiscal (19/08/2026): `reports/relatorio_<comp>_consolidado_PROTOTYPE.xlsx` com as 5 abas do núcleo financeiro, construído a partir dos ROMs reais MinC+MTur (com uma divergência sintética documentada no script, para o MTur não ser um espelho degenerado do MinC).

Formato validado: reutiliza `pyauditor.excel._style` (Arial 10, header branco-em-navy, bordas finas, freeze panes) e vai além — aplica os formatos numéricos de `docs/styleguide.md` que a produção (`capa.py`/`report.py`) ainda não tem: moeda (`R$#,##0.00`), percentual (escapado quando o valor já está em espaço-percentual vs. formato `%` nativo quando é fração), e borda superior + negrito nas linhas de total (GLOSAS "Valor Glosa", CALCULO_PAGAMENTO "Valor recomendado"). `CAPA_E_CONTROLE` do mock passou a espelhar o padrão título/header de `capa.py` (`TITLE_FONT`/`HEADER_FONT`+`HEADER_FILL`/`LABEL_FONT`).

Gap remanescente (não implementado no mock nem na produção): color-coding por função de célula (azul=hardcode, preto=fórmula mesma aba, verde=link entre abas) do styleguide — deixado para quando `consolidate` virar código de produção, não é bloqueador da forma do workbook.

Prototype capturado como fonte primária na branch `prototype/consolidated-workbook-mock` (commit `a7df79c`), fora do master.