# 05 — Medir por Categoria sem reimplementar gates + estratégia

**What to build:** o caminho de medição por Categoria (indicadores segmentados por Grupo executor) deixa de remontar manualmente a sequência de quality gates + dispacho por shape sobre as linhas já filtradas, e passa a pedir isso ao motor de medição — o mesmo que o caminho do indicador inteiro já usa. A sequência gate+estratégia passa a existir num único lugar do código, eliminando uma reimplementação que hoje vive no loop de medição da CLI e que já divergiu do backbone (mesma sequência em dois pontos).

**Blocked by:** nenhum — pode começar imediatamente (recomendado: depois de 04, com quem compartilha o objetivo de unificar duplicação).

**Status:** ready-for-agent

- [ ] Medir um indicador com categorias produz os mesmos ROMs/summaries de hoje (mesmos IDs derivados, mesmos números) — validado na rede de integração existente de `measure`/`split`.
- [ ] A sequência quality gates → estratégia não existe mais no loop de medição da CLI; todo caminho a delega ao motor (o mesmo para indicador inteiro e por categoria).
- [ ] Nenhuma mudança de contrato público da CLI (mesmos argumentos, mesmos artefatos).
- [ ] `uv run pytest`, `uv run ty check` e `uv run ruff check` verdes; cobertura não cai.

## Contexto (do relatório de fricção)

O loop de medição do `measure` reexecuta manualmente `QualityGateRunner` + `SHAPE_REGISTRY` para cada categoria derivada, duplicando a sequência que `measure()` já executa — duplicação que o `SourceBundle` do backbone existe para evitar.