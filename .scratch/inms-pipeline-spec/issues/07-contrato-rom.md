Type: grilling
Status: resolved
Blocked by: 03, 04

## Question

Qual o contrato exato do ROM Markdown por indicador — seções fixas, e o formato é um template por shape (N templates completos) ou um template genérico que renderiza o que cada strategy expõe?

## Answer

**Um template genérico + um renderer por shape só para a seção de memória de cálculo.** Seções fixas, idênticas para todo indicador (vêm do `QualityGateRunner`, não da strategy):
- Cabeçalho: `indicator.id`, `contractual_id`, competência, contrato.
- População: filtros de escopo aplicados, contagem inicial.
- Rejeições: tabela ID + motivo + regra de `quality_gates` violada.
- Resultado vs meta, penalidade.

A única seção que varia é a **memória de cálculo**: cada shape contribui seu próprio renderer (`ratio` mostra numerador/denominador únicos; `segmented_ratio` mostra as sub-linhas por categoria + soma; `count_difference` mostra os termos da diferença; `external_catalog_sum` mostra a lista de ocorrências com pontos). Gerar templates completos por shape duplicaria ~80% do conteúdo.
