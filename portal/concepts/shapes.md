# Os shapes de cálculo

O campo `calculation.shape` de cada `inms-<n>.yaml` seleciona uma das cinco
strategies registradas no `SHAPE_REGISTRY`. Os 14 indicadores do Anexo D se
reduzem a esses shapes, provados pelos CSVs reais de produção.

| Shape | O que calcula | Indicadores em produção (configs/) |
|---|---|---|
| `ratio` | numerador/denominador × 100 contra meta, penalidade linear | 1.1, 1.3, 1.6, 1.7, 1.11, 1.12 |
| `segmented_ratio` | sub-razões por categoria (Alta/Média/Baixa), soma de penalidades | 1.2 |
| `precomputed_table` | resultado já apurado por linha (percentual ou pontos), lido direto do CSV | 1.4, 1.5, 1.8, 1.9, 1.10, 1.13, 1.14 |
| `count_difference` | `CNI = QRC − QCSI` (diferença de contagem), penalidade fixa por unidade | (não usa em produção hoje) |
| `external_catalog_sum` | soma linear de pontos do catálogo Anexo E, maior-pontuação-vence | (não usa em produção hoje) |

> A spec `docs/spec/inms-pipeline.md` §2 lista `count_difference` para o INMS
> 1.10 e `external_catalog_sum` para o INMS 1.8; os configs de produção atuais
> os apuram via `precomputed_table` (a fiscalização passou a fornecer uma
> tabela de apuração pré-computada). Os dois shapes continuam implementados e
> testados (ver `config/`, `strategy/` e os schemas provisórios de digitação
> manual na spec §11.3/§2.2).

## `ratio`

- Agregação por `aggregation`: `count_distinct` (conta linhas filtradas),
  `sum` (soma colunas de tempo/dias) ou `precomputed` (1 linha por CSV, valor
  é o próprio percentual).
- `target.operator` (`>=`/`<=`) suporta metas invertidas (ex.: INMS 1.11 é "≤").
- Penalidade linear contínua, sem teto por degrau:
  `base_points + (shortfall / step_size_pct) × step_points`.
- Denominador zero → `conforms = true`, sem penalidade (nada a medir ≠ 0%).

## `segmented_ratio`

- Várias categorias, cada uma com filtro de denominador/numerador e
  `step_points` próprio, todas contra a mesma meta compartilhada.
- `result_pct` agregado = soma dos numeradores/soma dos denominadores (cabeçalho).
- Penalidade final = soma das penalidades por categoria; `conforms` só é
  verdadeiro quando a soma é zero (todas as categorias cumpriram a meta).

## `precomputed_table`

- Lê uma tabela de apuração por competência: 1 linha por ativo/serviço, cada
  uma já traz o resultado e tipicamente a penalidade (`penalty_column`), que é
  simplesmente somada (a fórmula varia por indicador).
- `result_is_percent: true` — cabeçalho = resultado ponderado por horas
  (`sum(numerador)/sum(base)*100`) quando `numerator_column`/`denominator_column`
  existem, senão a média aritmética dos percentuais.
- `result_is_percent: false` — valor por linha é soma de pontos (ex.: INMS 1.8
  PDT); o cabeçalho é `0.0`.

## `count_difference`

- `QRC` = filtro de recomendados, `QCSI` = implantados dentro dos recomendados.
- `result_pct = QCSI/QRC × 100` (meta do Anexo D é "= 100%"), mas a penalidade
  é `CNI × penalty_per_unit` (fixa por controle faltante), não derivada da meta.

## `external_catalog_sum`

- Cada linha do CSV aponta códigos do catálogo Anexo E (coluna de códigos,
  separador configurável). Se a ocorrência enquadra vários itens, entra apenas
  o de **maior pontuação** (dedup por ocorrência).
- Sem teto e sem multiplicador de reincidência. Não tem meta de percentual
  (`target` proibido no schema).

## Tabela de grupos (abas por grupo operacional)

O mapeamento indicador → grupo (`ATENDIMENTO_N1`, `MONITORAMENTO_NOC_SOC`,
`ATENDIMENTO_N2`, `OPERACAO_N3`) é definido por primeiro-match em
`src/pyauditor/excel/groups.py` — cada indicador aparece na **primeira** aba
que o lista, exceto os por-ativo de disponibilidade (1.4, 1.5, 1.14), que são
os únicos da aba `MONITORAMENTO_NOC_SOC`.

## Fontes primárias

- `src/pyauditor/config/models.py` — modelos por shape (schema).
- `src/pyauditor/engine/strategies/` — implementações.
- `configs/inms-*.yaml` — exemplos reais por shape.
- `docs/spec/inms-pipeline.md` §2, §3.