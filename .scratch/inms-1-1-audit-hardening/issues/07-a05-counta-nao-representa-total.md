# 07 — A-05: `COUNTA(Nº Solicitação)` não representa necessariamente o total de incidentes

**Severidade:** Alta

**Linhas afetadas:** 951, 959.

**Status:** needs-triage

## Problema

```python
last_row = 1 + len(rows)
iap = f"COUNTA({rng(_R)})"
```

`rows` pode conter um incidente com número da solicitação vazio. Nesse caso a
base tem uma linha a mais do que o `COUNTA` contabiliza, enquanto a nota da fonte
informa `len(rows)` — os dois totais divergem silenciosamente.

## Correção recomendada

Se cada item de `rows` representa um incidente, usar coluna auxiliar constante
(valor 1) ou `=ROWS($R$2:$R$N)` em vez de `COUNTA` sobre uma coluna que pode ter
células vazias. Tratar separadamente o caso do conjunto vazio.

Melhor ainda: validar na fronteira que número da solicitação não está vazio (e é
único, se essa for regra de domínio) — ver também ticket 12 (M-05, unicidade de mapeamento).

## Critério de aceite

- [ ] Contagem do IAP não depende de `COUNTA` sobre coluna que pode ter vazios
- [ ] Teste: número de solicitação vazio em um registro — total bate entre nota da fonte e IAP
- [ ] Teste: número de solicitação duplicado (matriz de testes do spec.md)
