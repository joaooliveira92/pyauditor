# 07 — A-05: `COUNTA(Nº Solicitação)` não representa necessariamente o total de incidentes

**Severidade:** Alta

**Linhas afetadas:** 951, 959.

**Status:** resolved

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

- [x] Contagem do IAP não depende de `COUNTA` sobre coluna que pode ter vazios
- [x] Teste: número de solicitação vazio em um registro — total bate entre nota da fonte e IAP
- [x] Teste: número de solicitação duplicado (matriz de testes do spec.md)

## Answer

`iap` trocou de `COUNTA($R$2:$R${last_row})` para `ROWS($R$2:$R${last_row})` —
`ROWS()` conta as linhas do range independentemente de conteúdo (vazio, texto,
duplicado), então o IAP sempre bate com `len(rows)` (o mesmo número exibido na
nota da fonte, Seção 1), inclusive quando `Nº Solicitação` vier vazio ou
duplicado. Não foi adicionada validação de unicidade/obrigatoriedade de `Nº
Solicitação` — o ticket já marca isso como "melhor ainda" opcional, e nenhuma
regra de negócio deste indicador depende de `Nº Solicitação` ser único (ele só
é usado para exibição/rastreabilidade nas Seções 6 e 7, via `INDEX`/`MATCH`
sobre outras colunas).

Teste: `test_iap_denominator_uses_rows_not_counta` em `tests/test_inms_1_1_audit.py`,
com um registro de `Nº Solicitação` vazio e dois registros duplicados (`"1"`)
— confirma `B13 = ROWS($R$2:$R$4)` e que a nota da fonte (`B6`) mostra "3
registros brutos", batendo com o range da base de apoio.
