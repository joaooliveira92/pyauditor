# 15 — M-06: Tabelas e nomes não são protegidos contra múltiplas chamadas

**Severidade:** Média

**Status:** needs-triage

## Problema

Os nomes de tabela (`TabelaGrupoExecutor`, `TabelaForaDoPrazo`,
`TabelaAmostraDivergencias`) são fixos. Nomes de tabela precisam ser únicos
dentro da pasta de trabalho inteira, não só dentro da aba. Se o renderer for
usado mais de uma vez no mesmo workbook, a criação de tabela falha.

## Correção recomendada

**Não é específico do INMS 1.1** — qualquer renderer que crie `Table` do
openpyxl tem o mesmo risco de colisão de nome dentro do workbook. Criar
`unique_table_name(workbook, base_name)` em `src/pyauditor/excel/_workbook.py`
(mesmo módulo do ticket 08 / A-06), que incorpora um identificador da aba e
verifica contra os nomes já existentes no workbook.

## Critério de aceite

- [ ] `unique_table_name()` implementada em `excel/_workbook.py`, usada pelas três tabelas do INMS 1.1
- [ ] Teste: duas abas enriquecidas no mesmo workbook (matriz de testes do spec.md) não colidem
