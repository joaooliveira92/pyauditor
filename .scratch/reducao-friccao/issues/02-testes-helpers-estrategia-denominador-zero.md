# 02 — Rede de testes dos helpers de estratégia e unificação da regra de denominador zero

**What to build:** testes unitários diretos para os helpers de filtragem, meta/pontuação e interpretação de penalidade que hoje só são exercitados por integração — e, com eles, a homologação e unificação de uma regra que hoje diverge: quando não há atividade no período (denominador zero), uma estratégia isenta de penalidade e declara conforme, enquanto outra penaliza como não-conformidade. A regra passa a ser única e compartilhada: denominador zero ⇒ sem base para penalizar (conforme, 0 pontos), deixando de existir um caminho que zera o resultado e aplica `shortfall` por engano.

**Blocked by:** nenhum — pode começar imediatamente.

**Status:** ready-for-agent

- [x] `filter_rows` (incluindo o filtro de duração), `safe_pct`, `meets_target`, `shortfall` e a leitura de penalidade têm teste unitário direto, com valores determinísticos.
- [x] A regra de denominador zero está traçada por uma função única usada por todas as estratégias com meta percentual — nenhuma aplica `shortfall` a resultado sem base (denominador zero zera silenciosamente).
- [x] O comportamento de homologação: os casos com atividade real do período seguem idênticos aos de hoje (mesmos números); só o caminho sem atividade muda onde hoje penalizava por bug.
- [x] Divergências comportamentais encontradas entre estratégias são documentadas no ticket (Answer) com o antes/depois de cada shape.
- [x] `uv run pytest`, `uv run ty check` e `uv run ruff check` verdes; cobertura não cai.

## Contexto (do relatório de fricção)

`ratio` trata denominador zero como sem-período (conforme, 0 pontos); o caminho segmentado confia em `safe_pct` retornando 0.0 e aplica `shortfall(0.0, …)`, penalizando. Bug no ponto de chamada, não na função pura. É a rede que destrava o ticket 06 (colunas por estratégia), pois centraliza o contrato comum de cálculo.

## Answer — divergências comportamentais (antes/depois)

Rede de testes novos e unificação da regra de denominador zero. Arquivos de teste:
`tests/test_target.py` (`safe_pct`, `meets_target`, `shortfall`, `ratio_penalty_points`),
`tests/test_filters.py` (`filter_rows`, incl. `DurationAtMost`),
`tests/test_penalty.py` (`penalty_interpretation`),
`tests/test_zero_denominator.py` (regressão de denominador zero em `ratio` e `segmented_ratio`).

A divergência encontrada foi exatamente a do contexto: `ratio` já tratava
denominador zero como sem-período (conforme, 0 pontos), enquanto `segmented_ratio`
penalizava por bug. Antes/depois de cada shape:

**`ratio` (sem atividade, ex. target `>= 90`, step 0.1, step_points 20, base 0)**
- Antes: `conforms=True`, `penalty_points=0.0` (já correto — inalterado).
- Depois: idêntico. Só o cálculo passou a rotear pela função única
  `ratio_penalty_points`.

**`segmented_ratio` — categoria sem atividade (denominador 0, ex. target `>= 90`,
step_size 0.1, step_points 20)**
- Antes (bug): `result_pct=0.0`, `penalty_points = shortfall(0.0)/0.1*20 = 18000`,
  `conforms=False` — categoria penalizada como não-conformidade.
- Depois: `result_pct=0.0`, `penalty_points=0.0`, `conforms=True` (regra única).

**Homologação — casos com atividade real (denominador > 0)**
- `ratio` não-conforme: `base + shortfall/step_size*step_points` — idêntico (a
  antiga `_linear_penalty` foi substituída pela função única sem mudar números).
- `ratio` conforme (incl. sub-meta dentro do EPSILON): 0 pontos (base não se
  aplica a indicador conforme) — idêntico.
- `segmented_ratio` por categoria: `shortfall/step_size*step_points` — idêntico,
  incluindo a borda exata (não-perdoadora) sub-meta: `ratio_penalty_points` usa
  `max(shortfall, 0)`, sem o EPSILON do `meets_target`, então um resultado real
  dentro do EPSILON abaixo da meta mantém a penalidade mínima de antes (travado
  em `test_target.py::test_ratio_penalty_is_exact_not_epsilon_forgiving`). O
  teste sintético existente `alta` 50% → 8000 p.p. permanece verde.

**`precomputed_table`**: sem caminho de denominador zero — as linhas já chegam com
o valor medido (vazias são puladas) e o headline usa `safe_pct` só com
`denominator_sum > 0`; não roteia pela função única por não ser ratio
denominador/numerador. Comportamento inalterado.

Gate: `uv run pytest` 636 passed (34 skipped), cobertura 89.70% (gate 85%, sem queda);
`uv run ty check` e `uv run ruff check` sobre `src/` e os arquivos tocados verdes. O
`ruff check .` do working tree reporta 10 achados pré-existentes em
`.claude/worktrees/feature-incidentes/pyproject.toml` (config de worktree, fora do
diff); `ruff format --check` aponta `tests/test_split_derive.py` pré-existente — nenhum
arquivo deste ticket.