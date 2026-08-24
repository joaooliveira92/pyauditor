# 01 — Rede de testes da matemática financeira

Type: task

**What to build:** testes unitários puros (sem instanciar workbook openpyxl) para os cálculos financeiros do pipeline, travando o comportamento atual antes de qualquer extração. Cobrem a glosa por ocorrência (`Valor Base × %Ajuste`), as faixas e a decisão de anistia, a glosa da competência (`MIN(Σ Pontos × 0.001, 30%) × valor mensal`) com teto e rollover, o rateio MinC/MTur e a computação de glosa do relatório por órgão. São a rede de segurança que destrava os tickets 03 e 04.

**Blocked by:** nenhum — pode começar imediatamente.

**Status:** resolved

- [x] Cada cálculo financeiro tem teste como função pura, chamando os símbolos de produção sem tocar em workbook.
- [x] Valores esperados determinísticos documentam o comportamento atual (não "golden" opaco).
- [x] Cobertura das funções-alvo não cai em relação à medição `--cov` anterior à alteração.
- [x] `uv run pytest` verde.

## Contexto (do relatório SRP)

Candidatos: `excel/consolidate/workbook.py` (`build_glosas`, `build_calculo`, `_glosa_bruto`, `_faixa`, `_decision_value`) e `excel/report.py` (`compute_report_glosa`). Existe `test_excel_consolidate_glosa_calcs.py` parcial — consolidar e ampliar.

## Answer

Criados dois arquivos de teste que travam a matemática financeira como funções puras:

- `tests/test_consolidate_glosa_math.py` — cobre `_glosa_bruto` (abaixo/teto/zero/por-órgão), `_faixa` (operadores `>=`/`<=`, detalhamento por-ativo), `_decision_value` (escalares vs. coerção a string), `compute_aggregation` (rateio do saldo anterior, zero pontos, teto de 30% no agregado) e `build_calculo` (linhas de rateio/bruto/pontos/glosa/recomendado com valores determinísticos, incluindo rateio MinC/MTur).
- `tests/test_report_glosa.py` — cobre `compute_report_glosa` (soma de pontos, teto/rollover, mês final, sem `valor_base`, zero pontos, consumo de saldo rolado e exclusão de sumário base quando há categoria derivada no mesmo `contractual_id`).

**Regressão encontrada e corrigida** (decidido com o usuário: corrigir agora): o refactor SRP anterior (commit `6ea370c`) removeu o espaço da label `Valordaglosa(=MIN(...))` em `excel/consolidate/workbook.py`, quebrando `label.startswith('Valor da glosa')` — a linha da glosa do `CALCULO_PAGAMENTO` passou a exibir `bruto - glosa` no lugar da glosa. Label restaurada para `Valor da glosa (= MIN(pontos x ..., ...%)/100 x bruto)`; teste dedicado trava o valor correto (`[0, 0, 150]` para 150 pontos sobre base 100.000).

Validação: `uv run pytest` 586 passed (era 560; +26 novos), cobertura total 89.38% (era 89.30%, não caiu); `workbook.py` subiu de 97% → 99%. `uv run ty check`, `uv run ruff check`, `uv run ruff format --check` e `uv run bandit` todos verdes.