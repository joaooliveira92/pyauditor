# Como o pipeline funciona

O pipeline apura **uma competência (mês) por vez**, por **um indicador por
config** (`inms-<n>.yaml`). Um único engine atende os 14 indicadores: o campo
`calculation.shape` do YAML seleciona uma *strategy* registrada.

## Visão geral do fluxo

```text
bootstrap ──► capa.xlsx (Excel de capa, idempotente)
                 │
measure  ──► para cada config em configs/:
                 │  1. descobre e valida os configs (Pydantic)
                 │  2. resolve o CSV (via manifest datasets.yaml ou csv direto)
                 │  3. lê o CSV (<data-dir>/<ano>/<mês>/)
                 │  4. roda quality gates (Qualidade de Dados)
                 │  5. strategy de cálculo pelo shape
                 │  6. escreve <id>.md (ROM) + <id>.json (sumário)
                 ▼
report   ──► lê os .json dos ROMs + capa + configs
                 ▼
           relatorio_<competencia>.xlsx (INMS_BASE + grupos + GLOSAS + ...)
```

Detalhes por camada:

1. **Config e schema (Pydantic).** O `IndicatorConfig` valida o YAML com
   modelos imutáveis e estritos. A validação em duas camadas distingue "config
   quebrada" (erro de schema, fail-rápido) de "dado rejeitado" (filtro de
   business, no passo 4).

2. **Descoberta de arquivos.** `discover_configs` varre `--config-dir` por
   `*.yaml`. Arquivos que não têm a chave `indicator` (ex.: `datasets.yaml`)
   são ignorados.

3. **Resolução do dataset.** Cada config referencia o CSV por `source.dataset`
   (um alias no manifesto `configs/datasets.yaml`) ou pelo campo legado
   `source.csv`. O manifesto resolve alias → arquivo + `delimiter` + `encoding`.

4. **Caminho de leitura por competência.** `measure <YYYY-MM>` lê os CSVs de
   `<data-dir>/<YYYY>/<MM>/`, nunca da raiz do `--data-dir` — assim um projeto
   guarda todas as aferições passadas lado a lado.

5. **Quality gates.** O `QualityGateRunner` aplica os `quality_gates.checks`
   declarados no YAML (hoje: `not_null` e `in_set`). Cada linha rejeitada vira
   um `RejectedRow(id, reason)` que alimenta a seção **Rejeições** do ROM. Se
   *todas as linhas existentes* forem rejeitadas, a medição é marcada como
   `hard_failure` (diferente de um CSV vazio de origem, sem linhas).

6. **Estratégia de cálculo.** O `SHAPE_REGISTRY` é um dict módulo-level
   (`shape → strategy`) com import explícito — sem plugin discovery. Cada
   strategy devolve um `CalculationResult` com `result_pct`, `conforms`,
   `penalty_points` e uma `memoria` específica do shape para o renderer do ROM.

7. **Saídas.** O `measure` grava, por indicador, `<sanitized-id>.md` (ROM) e
   `<sanitized-id>.json` (sumário flat via `IndicatorSummary`). O `report` lê
   **somente os JSONs** (não re-parseia o Markdown), junta a capa, os configs
   (para abas `CADASTROS`/`EVIDENCIAS`) e consolida `INMS_BASE`, abas por grupo
   e `GLOSAS`.

## Princípios de projeto

- **Validação em duas camadas**: Pydantic (config) e quality gates (dados).
- **Pipeline monólito por shape, não por indicador**: indicadores que não
  divergem estruturalmente compartilham a mesma strategy.
- **Multi-órgão**: `scope.orgao` aceita `MinC` e `MTur`; o `report` consolida
  os dois quando medem o mesmo indicador (fórmula ponderada — ver
  `docs/spec/inms-pipeline.md` §10).

## Fontes primárias

- `src/pyauditor/engine/pipeline.py` — orquestração.
- `src/pyauditor/engine/quality_gates.py` — camada de dados.
- `src/pyauditor/engine/strategies/__init__.py` — registry.
- `docs/spec/inms-pipeline.md` §3–§9.