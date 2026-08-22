# Testing progress

## Latest run

- Date: 2026-08-22
- Objective: Reparar as costuras de string acidentais e ligar o gate anti-regressão (wayfinder `suite-testes`, tickets 02 e 03)
- Outcome: Concluído — suíte verde, gate ligado sem falso positivo

## Baseline

- Tests: 559 passed, 34 skipped
- Branch coverage: 89.28% (gate `fail_under=85`)
- Failures: 0
- Skipped: 34 (não triados por causa — ver riscos conhecidos)

## Completed objectives

- `suite-testes/03`: reparo das ~90 costuras de string acidentais introduzidas pelo refactor em andamento (texto pt-BR/en colado sem espaço, ex. `ASCIIpositivo`). Suíte foi de 16 failed/543 passed para 559 passed/34 skipped.
- `suite-testes/02`: gate anti-regressão `ISC001`+`ISC003` (concatenação implícita de string numa única linha) no `[tool.ruff.lint]`. `ISC002` (multi-linha) ficou de fora — `allow-multiline = false` gerou 746 falsos positivos contra o estilo idiomático do repo (f-strings/tabelas Markdown construídas deliberadamente em várias linhas). 0 hits no código atual, sem `per-file-ignores`.

## Known risks

- `ty check` reporta 150 diagnósticos pré-existentes, fora do escopo deste esforço (ver mapa `migracao-ty`) — o workflow semanal (`weekly-testing.yml`) vai ficar vermelho nisso até essa dívida ser tratada em outro esforço.
- `bandit -r src` reporta 3 findings pré-existentes (B404/B603/B607, uso de `subprocess`) — mesmo status, fora de escopo aqui.
- 34 skips na suíte não foram triados por causa individual.
- Cobertura branch 89% está acima do gate (85%) mas não foi auditada por risco — o skill prioriza risco, não o número bruto.

## Recommended next objective

Triar os 34 skips e decidir, por risco, entre reativar, converter em `xfail` documentado ou remover cada um.
