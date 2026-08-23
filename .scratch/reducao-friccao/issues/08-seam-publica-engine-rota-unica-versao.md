# 08 — Seam pública do engine declarada e rota única de versão

**What to build:** o pacote do motor passa a declarar explicitamente a sua seam pública (hoje de facto centralizada num único módulo re-exportador), com os submódulos de suporte — descoberta de configs, leitura de CSV, versão — virando internos sem consumidores externos. A função de versão do pipeline passa a ser alcançável por uma única rota (hoje são duas). E o "furo" na seam declarada das estratégias — imports diretos a submódulo privado vindos de fora do pacote de estratégias — é corrigido, com todo consumidor externo passando pelos re-exports públicos.

**Blocked by:** nenhum — pode começar imediatamente.

**Status:** ready-for-agent

- [ ] A seam pública do motor está declarada e documentada; os submódulos de suporte não têm mais consumidores externos (deleção de um não quebra nada fora do pacote).
- [ ] A versão do pipeline é alcançável por exatamente uma rota de importação.
- [ ] Nenhum consumidor externo às estratégias importa de submódulo privado (o furo atual é fechado).
- [ ] `uv run pytest`, `uv run ty check` e `uv run ruff check` verdes; cobertura não cai.

## Contexto (do relatório de fricção)

A seam de facto é o re-exportador do pipeline (testes e CLI importam dele), enquanto os submódulos SRP existem sem consumidores externos; a mesma função de versão é alcançável por 2 rotas; e dois pontos importam de submódulo privado das estratégias contrariando a seam declarada.