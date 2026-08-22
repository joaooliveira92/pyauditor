# 05 — A-03: `target_operator == "<="` não é suportado semanticamente de ponta a ponta

**Severidade:** Alta

**Linhas afetadas:** 401–408, 443–450, 868–900.

**Status:** needs-triage

## Problema

O resumo e parte da penalidade invertem o operador corretamente, mas a memória de
cálculo continua orientada a meta mínima ("Quantidade mínima dentro do prazo p/
atingir a meta:", `=ROUNDUP(B13*A13,0)`) e a Seção 3 fixa "Desvio em pontos
percentuais (Resultado - Meta): =E13-A13". Para uma métrica com meta `<=`, os
conceitos de "quantidade mínima dentro do prazo" e "abaixo do mínimo" deixam de
fazer sentido.

Na Seção 9, o label é sempre "Diferença (Meta - Resultado)" mas a fórmula
`=E13-A13` calcula Resultado - Meta, contradizendo o próprio label.

## Correção recomendada

Escolher uma das duas opções:

1. Restringir este renderer a `target_operator == ">="`, falhando explicitamente
   (`ValueError`) para qualquer outro operador — mais simples e seguro se o
   domínio do INMS 1.1 garante meta mínima.
2. Implementar labels, fórmulas e narrativa específicos para cada direção de meta.

## Critério de aceite

- [ ] Decisão registrada (restringir vs. implementar as duas direções)
- [ ] Se restringir: `write_sheet()` valida `target_operator` na fronteira e falha com mensagem clara para `<=`
- [ ] Se implementar: labels e fórmulas da Seção 3 e Seção 9 corrigidos para refletir a direção correta da meta
- [ ] Teste: operador `<=` (ver matriz de testes do spec.md)
