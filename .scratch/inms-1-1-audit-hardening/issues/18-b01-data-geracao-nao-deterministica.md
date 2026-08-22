# 18 — B-01: Data de geração não é determinística

**Severidade:** Baixa

**Status:** needs-triage

## Problema

`datetime.now()` é usado diretamente, dificultando testes reproduzíveis.

## Correção recomendada

Injetar um parâmetro `generated_at`, com default opcional controlado na camada
chamadora (não dentro de `inms_1_1_audit.py`).

## Critério de aceite

- [ ] `write_sheet()` (ou função equivalente) aceita `generated_at` injetável
- [ ] Teste unitário usa `generated_at` fixo em vez de depender do relógio real
