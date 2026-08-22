# 21 — B-04: Estilos não são aplicados consistentemente

**Severidade:** Baixa

**Status:** needs-triage

## Problema

Na Seção 5, `pct` e tempo de N1/N2/N3 não recebem explicitamente `BODY_FONT`,
enquanto outros campos recebem. Não altera o cálculo, mas reduz consistência
visual.

## Correção recomendada

Aplicar `BODY_FONT` de forma consistente a todas as células de dados da Seção 5.

## Critério de aceite

- [ ] `pct` e tempo de N1/N2/N3 recebem `BODY_FONT` como os demais campos da Seção 5
