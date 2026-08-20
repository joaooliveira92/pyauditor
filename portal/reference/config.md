# Schema de config — `inms-<n>.yaml`

Referência dos blocos aceitos por um config de indicador. O YAML é validado por
modelos Pydantic imutáveis/estritos (`src/pyauditor/config/models.py`) — campos
desconhecidos falham.

## Estrutura geral

```yaml
indicator:       # obrigatório
  id: INMS-1.1
  contractual_id: "INMS 1.1"
  name: Incidentes atendidos dentro do prazo
  asset: null     # opcional — rótulo do ativo (por-ativo)
scope:           # obrigatório
  contract: "40/2022 - Ministério da Cultura"
  orgao: MinC     # MinC | MTur
source:          # obrigatório — exatamente UM de dataset|csv
  dataset: incidentes        # alias no manifesto datasets.yaml
  # csv: inms-001-01.csv     # caminho legado (alternativa)
  # delimiter: ";"
  # encoding: "utf-8-sig"
  # id_column: "Nº Solicitacao"
quality_gates:   # obrigatório (pode ser checks: [])
  checks:
    - type: not_null
      column: "DataHoraFim"
    - type: in_set
      column: "No prazo"
      values: ["S", "N"]
calculation:     # obrigatório — shape define o formato abaixo
  shape: ratio
  ...
target:          # opcional conforme shape (proibido em external_catalog_sum)
  operator: ">="     # ou "<="
  value: 98.0
penalty:         # opcional conforme shape
  base_points: 165
  step_points: 20
  step_size_pct: 0.1
acceptance_test: # opcional — esperado para o smoke test
  expected:
    shape: ratio
    numerator: 171
    denominator: 175
    result_pct: 97.71
    conforms: false
    penalty_points: 222.14
```

## Campos por sessão

### `indicator`

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `id` | string | sim | Identificador; vira nome de arquivo do ROM/JSON (sanitizado) |
| `contractual_id` | string | sim | Código contratual (ex.: `"INMS 1.1"`) |
| `name` | string | sim | Nome legível do indicador |
| `asset` | string\|null | não | Diferencia medições que compartilham `contractual_id` (1.4, 1.5, 1.14 por serviço) |

### `scope`

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `contract` | string | sim | Identificador do contrato |
| `orgao` | `"MinC"` \| `"MTur"` | não | Órgão; default `MinC`. `measure`/`report` são por órgão; `consolidate` funde os dois |

### `source`

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `dataset` | string | ou `csv` | Alias no `datasets.yaml` |
| `csv` | string | ou `dataset` | Nome do arquivo (legado) |
| `delimiter` | string | não | default `";"` |
| `encoding` | string | não | default `"utf-8-sig"` |
| `id_column` | string | não | Coluna de identificação p/ lista de rejeições; default `"Nº Solicitacao"` |

**Validação:** exatamente um de `dataset`/`csv`.

### `quality_gates.checks`

| `type` | Campos | Comportamento |
|---|---|---|
| `not_null` | `column` | rejeita se vazio ou `"null"` |
| `in_set` | `column`, `values[]` | rejeita se fora do conjunto |

### `calculation` por shape

#### `ratio`

```
shape: ratio
aggregation: count_distinct | sum | precomputed
numerator_filter:     # Filter | null (obrigatório p/ count_distinct)
  column: ...
  equals: ...          # ColumnEquals
  # contains: ...      # ColumnContains
  # in_values: [...]   # ColumnIn
  # max_seconds: N     # DurationAtMost (coluna H:MM:SS)
denominator_filter:   # mesmo formato, null
sum_numerator_column: "..."      # p/ sum
sum_denominator_extra_column: "..."  # p/ sum
precomputed_result_column: "..." # p/ precomputed (espera exatamente 1 linha)
```

### `segmented_ratio`

`step_size_pct` (> 0) + `categories[]`, cada uma com `name`,
`denominator_filter`, `numerator_filter` e `step_points`.

### `count_difference`

`recommended_filter` (Filter|null), `implemented_filter` (Filter), e
`penalty_per_unit` (>= 0).

### `external_catalog_sum`

`occurrence_id_column`, `catalog_codes_column`, `catalog_codes_separator`
(default `","`). **Não admite `target`.**

### `precomputed_table`

`result_column` (obrigatório), `result_is_percent` (default true),
`name_column`, `numerator_column`, `denominator_column`, `penalty_column`
(opcionais).

### `target` / `penalty`

- `target`: `operator` (`>=`\|`<=`) e `value` (0–100). Obrigatório para todo
  shape exceto `external_catalog_sum`.
- `penalty`: `base_points` (default 0), `step_points` (>= 0),
  `step_size_pct` (> 0). Obrigatório para `ratio` com meta.

### `acceptance_test`

`expected` com o shape correspondente (`RatioAcceptanceExpected`, etc.) —
usado pelo smoke test parametrizado (`tests/test_full_acceptance_smoke.py`).

## Exemplos reais

Os configs de produção vivem por órgão em `configs/<orgao>/` (ex.:
`configs/MinC/`), cada um com seu manifesto `datasets.yaml`.

- `ratio` — `configs/<orgao>/inms-1.1.yaml`.
- `segmented_ratio` — `configs/<orgao>/inms-1.2.yaml` (3 categorias por prioridade).
- `precomputed_table` — `configs/<orgao>/inms-1.8.yaml`, `configs/<orgao>/inms-1.10.yaml`.
- Fixtures para `count_difference` e `external_catalog_sum`: `tests/fixtures/manual_entry_examples/`.

O manifesto por órgão (`<config-dir>/<orgao>/datasets.yaml`) é o default de
`--manifest` em `measure`; se não existe, o `measure` usa `source.csv` e avisa.

## Fontes primárias

- `src/pyauditor/config/models.py` — definição exata dos campos e validações.
- `configs/<orgao>/*.yaml` — exemplos.
- `tests/fixtures/configs/` e `tests/fixtures/multi_asset_configs/`.