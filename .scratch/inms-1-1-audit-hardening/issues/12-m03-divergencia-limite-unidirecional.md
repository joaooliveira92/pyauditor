# 12 — M-03: Apenas divergências positivas de limite são consideradas

**Severidade:** Média

**Linhas afetadas:** 311–313, 758–764.

**Status:** needs-triage

## Problema

A regra atual é `lim > abertura + prazo + 1 minuto`. Um limite ITSM menor que o
limite contratual bruto não é classificado como divergência. Se a intenção é
comparar igualdade contratual com tolerância, o correto seria avaliar o valor
absoluto (`abs(lim - expected_limit) > tolerance`). Se só prorrogações indevidas
importam, o nome da coluna ("Divergência de prazo") está enganoso — sugere
comparação bidirecional quando não é.

## Correção recomendada

Decidir a semântica correta com o dono do domínio e então:

- se bidirecional: usar `abs(...)` na comparação
- se unidirecional (só prorrogação indevida): renomear a coluna para algo como
  "Limite ITSM superior ao prazo contratual bruto"

## Critério de aceite

- [ ] Semântica decidida e documentada
- [ ] Fórmula e/ou nome da coluna ajustados de forma consistente com a decisão
- [ ] Teste cobrindo o caso de limite ITSM menor que o contratual bruto
