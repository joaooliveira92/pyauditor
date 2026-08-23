# 07 — Render de memória e unidade de medida vêm da estratégia

**What to build:** o ROM e o Excel deixam de despachar por shape nos seus próprios registros paralelos. A estratégia passa a ser a fonte de verdade de duas coisas que hoje vivem fora do motor: a renderização da memória de cálculo (Markdown do ROM) e a unidade de medida do indicador (célula do Excel). Isso derruba dois registros shape-keyed mantidos à parte, que hoje podem divergir do registro de cálculo. Registrar um novo shape passa a exigir tocar só modelo + união + estratégia + registro de estratégias — não mais os pontos de apresentação.

**Blocked by:** 06 — estratégia como fonte de verdade das colunas referenciadas (estabelece o shape como módulo profundo com contrato rico antes de a apresentação passar a consultá-lo).

**Status:** ready-for-agent

- [ ] A renderização da memória de cada shape sai do registro paralelo e vem da própria estratégia; a saída Markdown dos cinco shapes atuais é idêntica à de hoje.
- [ ] A unidade de medida exposta no Excel deriva da estratégia, não de um mapa shape→unidade separado.
- [ ] Teste de deleção: registrar o sexto shape exige diffs só em modelo + união + estratégia + registro — e esse registro único é o `SHAPE_REGISTRY`.
- [ ] `uv run pytest`, `uv run ty check` e `uv run ruff check` verdes; cobertura não cai.

## Contexto (do relatório de fricção)

Três registros shape-keyed separados (`SHAPE_REGISTRY`, o dicionário de renderers de memória do ROM e o mapa shape→unidade do Excel) que podem divergir — o custo de registrar um shape é profundo, não raso.