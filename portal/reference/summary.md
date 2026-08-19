# Sumário JSON

Ao lado de cada ROM, o `measure` grava um `<id>.json` com o **sumário
estruturado** da medição. O `report` lê **somente** esses arquivos (não
re-parseia o Markdown). Esquema definido por `IndicatorSummary` em
`src/pyauditor/rom/summary.py`.

## Campos

| Campo | Tipo | Descrição |
|---|---|---|
| `indicator_id` | string | `indicator.id` do config |
| `contractual_id` | string | `indicator.contractual_id` |
| `name` | string | `indicator.name` |
| `asset` | string\|null | `indicator.asset` (null p/ indicador de ativo único) |
| `orgao` | string | `scope.orgao` |
| `shape` | string | shape de cálculo usado |
| `target_operator` | string\|null | `>=` \| `<=`, ou null sem meta |
| `target_value` | float\|null | meta, ou null sem meta |
| `result_pct` | float | resultado de cabeçalho do shape |
| `conforms` | bool | conformidade calculada |
| `penalty_points` | float | penalidade da medição |
| `numerator` | float\|null | numerador poolado (ratio/segmented_ratio) |
| `denominator` | float\|null | denominador poolado (ratio/segmented_ratio) |
| `hard_failure` | bool | true se TODAS as linhas existentes foram rejeitadas pelos gates |

> **Nota:** para `count_difference`, `numerator = QCSI` e `denominator = QRC`.
> Para `external_catalog_sum`/`precomputed_table` não há numerador/denominador
> no nível do indicador (null).

Exemplo:

```json
{
  "indicator_id": "INMS-1.1",
  "contractual_id": "INMS 1.1",
  "name": "Incidentes atendidos dentro do prazo",
  "asset": null,
  "orgao": "MinC",
  "shape": "ratio",
  "target_operator": ">=",
  "target_value": 98.0,
  "result_pct": 97.71,
  "conforms": false,
  "penalty_points": 222.14,
  "numerator": 171.0,
  "denominator": 175.0,
  "hard_failure": false
}
```

## Fontes primárias

- `src/pyauditor/rom/summary.py` — `IndicatorSummary`, `summarize`,
  `_pooled_numerator_denominator`.