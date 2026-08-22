# 09 — A-07: A regra de penalidade não valida parâmetros inválidos

**Severidade:** Alta

**Linhas afetadas:** 856–900.

**Status:** resolved

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

- [x] `write_sheet()` valida `target_operator`, `target_value` e `penalty_step_size_pct` na fronteira, falhando com `ValueError` claro
- [x] Teste: `penalty_step_size_pct == 0` levanta erro em vez de gerar `#DIV/0!` (matriz de testes do spec.md)
- [x] Teste: parâmetros fora de faixa (negativos, meta fora de 0–100) são rejeitados

## Answer

`_validate_write_sheet_params()` roda no início de `write_sheet()` (antes de
qualquer aba ser criada) e valida: `target_operator` deve ser `">="` (ver
ticket 05); `target_value` deve estar em `[0, 100]`; `penalty_base_points` e
`penalty_step_points` não podem ser negativos; `penalty_step_size_pct` deve
ser positivo (é divisor nas fórmulas da Seção 9 — `0` ou negativo gerariam
`#DIV/0!`/sinal invertido). Cada violação levanta `ValueError` com o nome do
parâmetro e o valor recebido.

Não foi adicionada validação explícita de NaN/infinito: `float("nan") <= 100`
e `float("nan") >= 0` são ambos `False` em Python, então um `target_value` NaN
já cai automaticamente fora do range `0 <= target_value <= 100` e é rejeitado
pela mesma checagem — não precisa de `math.isnan()` dedicado.

Testes: `test_out_of_range_params_are_rejected` (parametrizado com
`target_value` 150 e -1, `penalty_base_points` -1, `penalty_step_points` -1,
`penalty_step_size_pct` 0 e -0.1) em `tests/test_inms_1_1_audit.py`.
