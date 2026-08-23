# 09 — Relatório sintético consome a aritmética do motor

**What to build:** a camada de apresentação do relatório sintético para de reimplementar a aritmética de cálculo das estratégias sobre linhas cruas (agregação do ratio, verificação de meta atingida, conversão decimal) e passa a consumir a aritmética publicada pelo motor — a mesma que produz os resultados apurados. A apresentação deixa de acoplar-se à implementação interna do cálculo e o relatório e a apuração não podem mais divergir na regra.

**Blocked by:** 07 — render de memória e unidade vêm da estratégia (estabelece a apresentação consultando a estratégia) e 08 — seam pública do engine declarada (dá a rota pública pela qual a aritmética é consumida).

**Status:** ready-for-agent

- [ ] O relatório sintético usa a aritmética publicada pelo motor para agregar, converter decimal e decidir "meta atingida" — nenhuma reimplementação da regra na camada de apresentação.
- [ ] O conteúdo exibido por cada aba sintética (valores, agrupamentos, labels) é idêntico ao de hoje para os casos cobertos pelos testes existentes.
- [ ] `uv run pytest`, `uv run ty check` e `uv run ruff check` verdes; cobertura não cai.

## Contexto (do relatório de fricção)

As abas do sintético importam helpers do motor e reimplementam a aritmética de `_aggregate` (a própria docstring admite "com a mesma aritmética de `RatioStrategy._aggregate`"), além de reimplementarem meta e conversão decimal — apresentação acoplada ao motor de cálculo.