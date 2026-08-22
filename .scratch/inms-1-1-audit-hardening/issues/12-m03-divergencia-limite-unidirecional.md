# 12 — M-03: Apenas divergências positivas de limite são consideradas

**Severidade:** Média

**Linhas afetadas:** 311–313, 758–764.

**Status:** resolved

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

- [x] Semântica decidida e documentada
- [x] Fórmula e/ou nome da coluna ajustados de forma consistente com a decisão
- [x] Teste cobrindo o caso de limite ITSM menor que o contratual bruto

## Answer

Decisão: manter unidirecional (só sinalizar prorrogação indevida — limite ITSM
maior que o contratual bruto), renomear em vez de tornar bidirecional. Um
limite ITSM *menor* que o contratual bruto é mais rígido que o exigido
contratualmente — não é uma violação, é o fornecedor sendo mais restritivo do
que precisava; sinalizar isso como "divergência" no mesmo sentido que uma
prorrogação indevida confundiria o auditor sobre qual dos dois casos precisa de
atenção.

Renomeações: cabeçalho da coluna `_AC` ("Divergência de prazo" →
"Limite ITSM superior ao contratual bruto"), cabeçalho da coluna de ordenação
`_AI` ("Ordem — divergência de prazo" → "Ordem — limite ITSM superior ao
contratual bruto"), rótulos da Seção 7 ("Registros com limite divergente:" →
"Registros com limite ITSM superior ao contratual bruto:", título da amostra,
nota explicativa reforçando que "um limite ITSM inferior ao contratual bruto
não é sinalizado"). A fórmula em si (`vc > abc + tolerância` → "Sim"/"Não") não
mudou — já era unidirecional, só o nome não deixava isso explícito.

Testes: `test_limite_itsm_column_renamed_unidirectional` (novo cabeçalho da
coluna `AC`) e `test_limite_itsm_menor_que_contratual_bruto_nao_e_sinalizado`
(limite ITSM de 1h, mais rígido que o contratual bruto de 2h — a amostra de
divergências da Seção 7, cuja contagem é calculada em Python e não depende de
recálculo de fórmula, permanece vazia) em `tests/test_inms_1_1_audit.py`.
