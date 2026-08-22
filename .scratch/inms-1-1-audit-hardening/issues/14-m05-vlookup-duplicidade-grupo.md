# 14 — M-05: Mapeamento por VLOOKUP pode mascarar duplicidade de grupo

**Severidade:** Média

**Linhas afetadas:** 273–303.

**Status:** resolved

## Problema

Se um grupo aparecer mais de uma vez em `grupo_rows` com categorias diferentes,
`VLOOKUP(..., FALSE)` retorna silenciosamente a primeira ocorrência. Não há
validação de unicidade de `grupo_rows`.

## Correção recomendada

```python
duplicates = ...
if duplicates:
    raise ValueError("Grupo executor associado a múltiplas categorias")
```

Validar antes de escrever a planilha.

## Critério de aceite

- [x] Validação de unicidade de grupo em `grupo_rows` implementada, falhando com mensagem clara
- [x] Teste: grupo mapeado em duas categorias (matriz de testes do spec.md)

## Answer

Investigação mostrou que essa validação **já existe** em uma camada mais baixa:
`compute_categoria_values()` (`src/pyauditor/categoria_filter.py`), chamada por
`_build_grupo_rows()` logo no início, já valida que nenhum `Grupo_executor`
pertence a mais de uma categoria — tanto por sobreposição de `in_values`
explícitos entre categorias quanto por `catch_all_contains` que tentasse
reivindicar um valor já capturado por outra categoria — e levanta `ValueError`
antes mesmo de `per_categoria_values`/`outros_values` existirem. Isso já valia
para `_write_grupo_executor_sheet` (o renderer genérico) e, por construção, já
valia para `_build_grupo_rows` também, já que ambos chamam a mesma função.

Não foi adicionado código de validação redundante em `inms_1_1_audit.py` — só
um comentário em `_build_grupo_rows()` explicando por que a validação de
unicidade não precisa ser duplicada ali (uma tentativa inicial de adicionar
essa checagem foi revertida ao descobrir, rodando os testes, que ela nunca
seria alcançada: `compute_categoria_values` sempre lança primeiro).

Teste: `test_duplicate_grupo_with_different_categories_raises` em
`tests/test_inms_1_1_audit.py`, construindo duas categorias com o mesmo
`in_values: ["N1"]` e confirmando que `_build_grupo_rows()` propaga o
`ValueError` de `compute_categoria_values` ("categorias devem ser disjuntas").
O mesmo cenário, passado por `write_sheet()` completo, também serve de teste
de regressão para o ticket 17 (M-08, criação atômica de aba) —
`test_write_sheet_atomic_rollback_on_duplicate_grupo`.
