# 06 — xlsx sintético: composição multi-ativo (INMS 1.14)

**What to build:** a aba do INMS 1.14 no `sintetico.xlsx` (`docs/spec/inms-pipeline.md` §14.5),
estendendo o gerador do ticket 05 para o único caso de composição Categoria × Ativo do Anexo D.

INMS 1.14 participa de 2 categorias (`MONITORAMENTO_NOC_SOC`, `OPERACAO_N3`, ambas
`whole_indicator`) e já tem 6 medições independentes por ativo (File Server, Telefonia, Mensageria,
Servidores de impressão, WI-FI, Rede — feature multi-asset existente, `Indicator.asset`,
`inms-14-<asset-slug>.yaml`). Não há cálculo novo aqui: as 6 medições por ativo já existem; este
ticket só duplica/rotula essas 6 medições sob as 2 categorias na apresentação (`whole_indicator`
significa "sem filtro de Grupo_executor", não "colapsa os ativos").

Na aba do 1.14, a coluna `Grupo executor` é substituída por **`Ativo`**, com 12 linhas (6 ativos × 2
categorias) agrupadas e subtotalizadas por categoria (bloco `MONITORAMENTO_NOC_SOC`, depois bloco
`OPERACAO_N3`) — mesmo padrão de linhas agrupadas com subtotal do ticket 05, sem estrutura de aba
nova.

**Blocked by:** 05

**Status:** resolved

- [x] Aba do INMS 1.14 no `sintetico.xlsx` usa coluna `Ativo` em vez de `Grupo executor`
- [x] 12 linhas (6 ativos × 2 categorias), lendo as 6 medições por ativo já existentes — nenhuma
      medição nova é calculada
- [x] Linhas agrupadas e subtotalizadas por categoria (bloco NOC/SOC, depois bloco Operação N3)
- [x] Teste de integração cobrindo a aba do 1.14 especificamente (fixtures multi-asset já existentes
      em `tests/fixtures/multi_asset_configs/`, se aplicável)
- [x] `uv run mypy --strict src` e `uv run pytest` verdes

**Nota de implementação:** o dataset real de 1.14 (`configs/*/inms-14.yaml`) usa `shape:
precomputed_table` com `name_column` — um único CSV, uma linha por ativo (spec §2.1) — não a
convenção `Indicator.asset`/`inms-14-<asset-slug>.yaml` (que só existe como fixture sintética em
`tests/fixtures/multi_asset_configs/`, nunca usada em produção; opera no nível `measure`/`report`
via `summary.json`, que `sintetico.xlsx` não lê). A aba do 1.14 lê o CSV real via o mesmo fluxo
`base_config_stem`/`resolve_source`/`read_raw_csv` dos demais INMS e agrupa por `name_column`
(`Ativo`) em vez de reusar as fixtures de multi-asset-file-discovery.
