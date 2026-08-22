# 22 — B-05: Nomes e contratos de retorno são inconsistentes

**Severidade:** Baixa

**Status:** needs-triage

## Problema

Algumas funções dizem retornar "última linha ocupada", mas no caso sem
ocorrências a função da Seção 6 retorna a própria linha da nota. Funciona no
encadeamento atual por acidente de implementação, não por contrato explícito.

## Correção recomendada

Padronizar todas as funções de seção para sempre retornar `next_free_row`,
documentando o contrato no docstring/type hint.

## Critério de aceite

- [ ] Todas as funções de seção retornam `next_free_row` de forma consistente
- [ ] Contrato documentado (docstring) em cada função afetada
- [ ] Teste garante que o encadeamento entre seções continua correto após a padronização
