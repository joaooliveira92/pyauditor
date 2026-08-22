# 14 — M-05: Mapeamento por VLOOKUP pode mascarar duplicidade de grupo

**Severidade:** Média

**Linhas afetadas:** 273–303.

**Status:** needs-triage

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

- [ ] Validação de unicidade de grupo em `grupo_rows` implementada, falhando com mensagem clara
- [ ] Teste: grupo mapeado em duas categorias (matriz de testes do spec.md)
