# 22 — B-05: Nomes e contratos de retorno são inconsistentes

**Severidade:** Baixa

**Status:** resolved

## Problema

Algumas funções dizem retornar "última linha ocupada", mas no caso sem
ocorrências a função da Seção 6 retorna a própria linha da nota. Funciona no
encadeamento atual por acidente de implementação, não por contrato explícito.

## Correção recomendada

Padronizar todas as funções de seção para sempre retornar `next_free_row`,
documentando o contrato no docstring/type hint.

## Critério de aceite

- [x] Todas as funções de seção retornam `next_free_row` de forma consistente
- [x] Contrato documentado (docstring) em cada função afetada
- [x] Teste garante que o encadeamento entre seções continua correto após a padronização

## Answer

Antes desta correção, cada `_write_section_N_*` devolvia a "última linha
ocupada" e `write_sheet()` somava `+ 2` em cada chamada para calcular o
`start_row` da seção seguinte — funcionava, mas o "+2" espalhado em `write_sheet()`
era o contrato implícito, não a função em si (e o caso sem incidentes da Seção
6 já retornava a linha da própria nota, que já era "última linha ocupada" —
description do ticket estava um pouco imprecisa aqui, mas o espírito do
problema — contrato implícito em vez de explícito — procede).

Padronizado: cada função de seção agora soma o espaçamento internamente e
devolve `next_free_row` — a linha livre onde a seção seguinte deve começar.
`write_sheet()` passa esse valor direto como `start_row` da próxima seção, sem
nenhuma aritmética própria. Docstring de cada função atualizada para
"Devolve `next_free_row` — ...". Seções 1-3 continuam de linhas fixas (não
dependem do volume de incidentes) e devolvem uma constante (16, 28)
consistente com o mesmo contrato.

Teste: nenhum teste novo dedicado (seria redundante) — todo o encadeamento
entre seções já é exercitado pelos testes existentes que localizam cada barra
de seção (`SEÇÃO 4`, `SEÇÃO 5`, ...) dinamicamente via
`sheet.iter_rows(...)` e leem células dentro delas; a suíte completa
(475 testes) passando após a padronização já é a evidência de que o
encadeamento permanece correto.
