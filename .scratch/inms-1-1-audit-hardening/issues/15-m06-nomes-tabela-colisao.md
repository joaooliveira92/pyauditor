# 15 — M-06: Tabelas e nomes não são protegidos contra múltiplas chamadas

**Severidade:** Média

**Status:** resolved

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

- [x] `unique_table_name()` implementada em `excel/_workbook.py`, usada pelas três tabelas do INMS 1.1
- [x] Teste: duas abas enriquecidas no mesmo workbook (matriz de testes do spec.md) não colidem

## Answer

`unique_table_name(workbook, base_name)` criada em `excel/_workbook.py`: coleta
os nomes de todas as `Table` já existentes em qualquer aba do workbook e, se
`base_name` colidir, sufixa `_2`, `_3`, ... até achar um nome livre.
`write_sheet()` resolve os três nomes (`TabelaGrupoExecutor`,
`TabelaForaDoPrazo`, `TabelaAmostraDivergencias`) uma vez, antes de escrever
qualquer seção, e repassa cada um via parâmetro `table_name` para
`_write_section_4_detalhamento`, `_write_section_6_fora_prazo` e
`_write_section_7_auditoria`.

Testes: `test_unique_table_name_returns_base_name_when_free`,
`test_unique_table_name_suffixes_on_collision` e
`test_unique_table_name_skips_multiple_collisions` em
`tests/test_excel_workbook.py` (unitários do utilitário); e
`test_write_sheet_twice_in_same_workbook_uses_unique_table_names` em
`tests/test_inms_1_1_audit.py`, chamando `inms_1_1_audit.write_sheet()` duas
vezes no mesmo `Workbook()` (duas abas) e confirmando que a segunda tabela
`TabelaGrupoExecutor` foi criada como `TabelaGrupoExecutor_2`.
