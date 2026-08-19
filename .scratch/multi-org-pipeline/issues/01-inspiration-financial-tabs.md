Type: research
Status: resolved

## Question

Inspecionar `inspiration-spreadsheet/afericao_06_2026.xlsx` (e cruzar com `docs/spreadsheet.md`) e documentar a estrutura das abas financeiras que o `consolidate` (2.1) precisa reproduzir:

- `CALCULO_PAGAMENTO` — quais colunas, o que é pré-preenchido, o que é fórmula, como o valor da glosa/pagamento é calculado a partir dos indicadores e do valor mensal.
- `GLOSAS` — layout, valores por indicador, base para o percentual de ajuste.
- `SERVICOS_POR_ORGAO` — como o detalhe por órgão/serviço é organizado.
- `CAPA_E_CONTROLE` — os campos financeiros que alimentam o cálculo.

Capturar também qualquer estrutura por-órgão vs por-indicador e as fórmulas/regras financeiras visíveis (não inferir além do que a planilha mostra).

Saída esperada: documento `.scratch/multi-org-pipeline/research/01-inspiration-financial-tabs.md` com a estrutura observada + gist do que o 2.1 deve reproduzir.

## Answer

Inspecionado `inspiration-spreadsheet/afericao_06_2026.xlsx` (17 abas) com openpyxl e contrastado com `docs/spreadsheet.md`.

Estrutura financeira chave:

- **`CAPA_E_CONTROLE`**: `B20` Valor Mensal Vigente = 481.534,80; `B21` Valor Global Anual = ×12. Esse valor alimenta `CADASTROS!B45`, `CALCULO_PAGAMENTO!B6` e o `Valor Base` de `GLOSAS`.
- **`SERVICOS_POR_ORGAO`**: matriz fixa de 9 serviços (linhas 4–12, cols A–F), booleana, não numérica; todas `Sim/Sim/Sim` com `Critério de Rateio` = `Chamados, ativos ou valor definido`.
- **`GLOSAS`**: 9 ocorrências (linhas 4–12) por indicador × por órgão (MinC/MTur) com Resultado/Meta/Faixa/%Ajuste/Valor Base/Valor Glosa. `Valor Glosa` por linha = `Valor Base × %Ajuste / 100`. `Total de Pontos` (47592.63) = Σ(col I)×1000; `Valor Glosa` final = `MIN(pontos×0.001, 30%) × mensal` = 144.460,44.
- **`CALCULO_PAGAMENTO`**: parâmetros (B6 mensal, B7 limite 0.3, B8/C9 rateio 0.5/0.5 provisório) + tabela MinC/MT/Consolidado. `D15` = `=MIN(D14*0.001,$B$7*100)/100*D13`; `D17` recomendado = `MAX(0, bruto−glosa)`. **O valor `pontos de glosa` (`D14`/`GLOSAS!B16`) é manual, não fórmula viva** — a cadeia indicador→pontos→glosa não está automatizada no workbook.
- **`CADASTROS`**: `Regras de Glosa` = `Ajuste_NMS(%) = Pontos x 0,001`, teto 30%. `%Ajuste` verificado = `(déficit/passo) × pontos-por-passo × 0.001` para 1.4/1.7/1.11/1.12/1.14; `1.2` usa regra manual por prioridade.

Ponto chave para 2.1: a cadeia indicador→pontos→glosa não está automatizada no workbook; `consolidate` precisa reconstrui-la a partir de `INMS_BASE` e do detalhe de `CADASTROS`/`CALCULO_PAGAMENTO`.

Detalhe completo e coordenadas celulares: `.scratch/multi-org-pipeline/research/01-inspiration-financial-tabs.md`.