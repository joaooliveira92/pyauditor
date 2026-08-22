# 16 — M-07: `_build_grupo_rows()` usa string vazia para categorias conhecidas sem nível

**Severidade:** Média

**Linhas afetadas:** 202.

**Status:** needs-triage

## Problema

```python
nivel = _NIVEL_BY_CATEGORIA.get(categoria_key, "")
```

O comentário do próprio código explica que célula vazia causa problemas nos
filtros, e `_SEM_NIVEL` é usado para esse fim em `outros_values` — mas uma nova
categoria não presente em `_NIVEL_BY_CATEGORIA` cai exatamente no caso `""` que o
comentário tenta evitar.

## Correção recomendada

```python
nivel = _NIVEL_BY_CATEGORIA.get(categoria_key, _SEM_NIVEL)
```

Ou, se toda categoria deveria obrigatoriamente ter nível configurado, falhar
explicitamente em vez de usar um default silencioso.

## Critério de aceite

- [ ] `_build_grupo_rows()` usa `_SEM_NIVEL` (ou falha) para categoria sem nível configurado
- [ ] Teste: categoria conhecida sem nível configurado (matriz de testes do spec.md)
