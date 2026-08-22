# 18 — B-01: Data de geração não é determinística

**Severidade:** Baixa

**Status:** resolved

## Problema

`datetime.now()` é usado diretamente, dificultando testes reproduzíveis.

## Correção recomendada

Injetar um parâmetro `generated_at`, com default opcional controlado na camada
chamadora (não dentro de `inms_1_1_audit.py`).

## Critério de aceite

- [x] `write_sheet()` (ou função equivalente) aceita `generated_at` injetável
- [x] Teste unitário usa `generated_at` fixo em vez de depender do relógio real

## Answer

`write_sheet()` ganhou o parâmetro obrigatório `generated_at: datetime` (sem
default — força quem chama a decidir, em vez de esconder `datetime.now()`
dentro do renderer). A camada chamadora,
`write_sintetico_workbook()` em `sintetico.py`, ganhou `generated_at:
datetime | None = None`, resolvendo `datetime.now()` uma única vez no início
da função (se não informado) e repassando o mesmo valor para todas as chamadas
de `inms_1_1_audit.write_sheet()` dentro do loop — como pedido, o default fica
na camada chamadora, não dentro de `inms_1_1_audit.py`.

Teste: `test_generated_at_is_injectable` em `tests/test_inms_1_1_audit.py`,
chamando `write_sintetico_workbook(..., generated_at=datetime(2020, 1, 1, 10, 30))`
e verificando que a célula "Data de geração" da Seção 1 tem exatamente esse
valor, não o relógio real.
