# 04 — Um único parser de CSV bruto

**What to build:** o pipeline passa a ter um único parser de CSV bruto — o que normaliza o alias `Grupo executor` → `Grupo_executor` do cabeçalho — usado por todos os caminhos de medição. O segundo leitor, que não normaliza esse alias e hoje só é usado por teste de inspeção, é removido, e os testes que o inspecionavam passam a usar o parser único. Resultado: uma só semântica de leitura bruta para o projeto, sem dois parsers com normalização divergente.

**Blocked by:** nenhum — pode começar imediatamente.

**Status:** ready-for-agent

- [ ] A leitura do CSV bruto em todo o pipeline faz a normalização do cabeçalho (alias `Grupo executor`); nenhum caminho de produção usa o parser legado que não normaliza.
- [ ] O parser legado duplicado é removido (sem consumidores de produção); os testes que o inspecionavam migram para o parser único com o mesmo comportamento verificado.
- [ ] Comportamento de linhas irregulares (overflow) preservado e coberto no parser único.
- [ ] `uv run pytest`, `uv run ty check` e `uv run ruff check` verdes; cobertura não cai.

## Contexto (do relatório de fricção)

Dois parsers de CSV com normalização de header divergente — um usado no backbone e um que não normaliza o alias `Grupo executor` (confirmado em produção: alguns exports usam espaço). O legado não tem consumidores em produção.