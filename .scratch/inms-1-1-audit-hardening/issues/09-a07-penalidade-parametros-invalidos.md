# 09 — A-07: A regra de penalidade não valida parâmetros inválidos

**Severidade:** Alta

**Linhas afetadas:** 856–900.

**Status:** needs-triage

## Problema

Não há validação local para `penalty_step_size_pct`. Se for zero, as fórmulas
`B{diffpp_row}/{penalty_step_size_pct}` e `CEILING(...)/{penalty_step_size_pct}`
geram divisão por zero. Também não há defesa contra penalidade-base negativa,
pontos por faixa negativos, meta fora de 0–100, operador diferente de `>=`/`<=`,
NaN/infinito, ou percentuais fornecidos em formato fracionário. O comentário do
código diz que o operador foi validado pelo Pydantic, mas a função pública
continua aceitando `str`/`float` irrestritos.

## Correção recomendada

Validar na fronteira de `write_sheet()` ou usar tipos de domínio:

```python
if target_operator not in {">=", "<="}:
    raise ValueError(...)

if not 0 <= target_value <= 100:
    raise ValueError(...)

if penalty_step_size_pct <= 0:
    raise ValueError(...)
```

## Critério de aceite

- [ ] `write_sheet()` valida `target_operator`, `target_value` e `penalty_step_size_pct` na fronteira, falhando com `ValueError` claro
- [ ] Teste: `penalty_step_size_pct == 0` levanta erro em vez de gerar `#DIV/0!` (matriz de testes do spec.md)
- [ ] Teste: parâmetros fora de faixa (negativos, NaN, meta fora de 0–100) são rejeitados
