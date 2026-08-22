# 16 — M-07: `_build_grupo_rows()` usa string vazia para categorias conhecidas sem nível

**Severidade:** Média

**Linhas afetadas:** 202.

**Status:** resolved

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

- [x] `_build_grupo_rows()` usa `_SEM_NIVEL` (ou falha) para categoria sem nível configurado
- [x] Teste: categoria conhecida sem nível configurado (matriz de testes do spec.md)

## Answer

Correção exatamente como sugerida: `_NIVEL_BY_CATEGORIA.get(categoria_key, "")`
→ `_NIVEL_BY_CATEGORIA.get(categoria_key, _SEM_NIVEL)`. Uma linha.

Teste: `test_categoria_sem_nivel_configurado_usa_sem_nivel_sentinela` em
`tests/test_inms_1_1_audit.py`, com um `categorias.yaml` de duas categorias
(`ATENDIMENTO_N1`, presente em `_NIVEL_BY_CATEGORIA`, e `SUPORTE_ESPECIAL`,
ausente) — confirma que a linha do grupo mapeado em `SUPORTE_ESPECIAL` recebe
`_SEM_NIVEL` ("—"), não `""`, na coluna "Nível" da Seção 4.
