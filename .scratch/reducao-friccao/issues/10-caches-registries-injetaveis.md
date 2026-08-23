# 10 — Caches e registries injetáveis

**What to build:** os carregadores com cache global de catálogo Anexo E, de `categorias.yaml` e de manifest passam a aceitar um provider de cache injetável (opcional), mantendo o comportamento de produção idêntico. Os testes deixam de manipular o cache interno exposto (limpar cache para revalidar o carregamento) e passam a injetar um provider descartável por teste. Registries globais não-injetáveis deixam de ser conhecimento que o teste precisa ter da implementação.

**Blocked by:** nenhum — pode começar imediatamente.

**Status:** ready-for-agent

- [ ] Produção: os três carregadores mantêm exatamente o comportamento atual (cache global, resultados imutáveis) quando o provider não é informado.
- [ ] Testes: nenhum teste toca mais a API interna de limpeza de cache; cada teste que precisa revalidar o carregamento usa provider próprio.
- [ ] `uv run pytest`, `uv run ty check` e `uv run ruff check` verdes; cobertura não cai.

## Contexto (do relatório de fricção)

`load_anexo_e_catalog` (com cache limitado) e `load_categorias` (cache sem limite) expõem a implementação de cache; os testes chamam a limpeza direto, o que os acopla à implementação do decorator.