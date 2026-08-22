# 04 — Operacionalizar o ciclo semanal de testes e coordenar o CI

Type: grilling
Status: resolved
Label: wayfinder:grilling
Blocked by: 02, 03

## Question

Com a suíte verde (ticket 03) e o gate anti-costura decidido (ticket 02), decidir o mecanismo que **operacionaliza o `python-testing-evolution`** a partir do repo:

- Layout: `.testing-progress/state.json` conforme o schema do skill, `notes/testing-progress.md` mantido, `scripts/validate_state.py` como gate local — iniciar já ou só quando o primeiro ciclo semanal rodar?
- Workflow semanal de testes (GitHub Actions): `cron` semanal + `workflow_dispatch`, permissões read-only, rodando o baseline completo (pytest com cobertura, ruff check/format, ty, bandit, pip-audit).
- Coordenação com o `migracao-ty`: este mapa já assume um workflow de qualidade `ty` + `ruff` (+ pytest) — **decidir**: workflow único (um só coroutine, mais barato) vs workflow de testes separado; quem é dono do gate de qualidade.
- Política de escalada: com permissões read-only, o workflow publica relatório como artefato — como o agente/humano é acionado se a semana pagar (sem PR/merge automático).
- Onde ancorar a "próxima objective" semanal (o sinal de higiene do fog — skips, cobertura subindo).

Resolução: `## Answer` + fechamento + contexto no [map]. Configurações (cron, nexentias) migram para `pyproject.toml`/`.github/workflows/` como assets linkados.

## Answer

**Iniciar o layout agora** (não esperar o primeiro ciclo semanal), com um
**workflow único**.

- `.testing-progress/state.json`: criado a partir do template do skill, com
  o baseline real já medido nesta sessão (559 passed / 34 skipped / 0
  failures / 89.28% branch coverage), `completed_objectives` preenchido com
  os tickets 02 e 03, `known_risks` com as dívidas descobertas (`ty` 150
  diagnósticos, `bandit` 3 findings, 34 skips não triados), e
  `next_objective` apontando para a triagem dos skips. Validado contra
  `references/state.schema.json` via `scripts/validate_state.py` — OK.
- `notes/testing-progress.md`: espelha o `state.json` em prosa, template do
  skill.
- `scripts/assess_project.py`: copiado do skill, adaptado ao layout real do
  repo (`tests/acceptance/**` no lugar de `tests/unit`/`tests/integration`,
  que não existem aqui).
- **Workflow único** `.github/workflows/weekly-testing.yml`: não havia
  workflow de qualidade prévio do `migracao-ty` no repo (só `docs.yml` e
  `static.yml` existiam) — nada para coordenar/duplicar, então o workflow
  semanal já cobre a cadeia completa (`ruff check`+`format --check`, `ty
  check`, `pytest` com cobertura branch + JUnit, `bandit`, `pip-audit`) num
  job só. Se o `migracao-ty` criar depois um workflow de qualidade dedicado,
  revisar para não duplicar execução — mas hoje um workflow é mais barato e
  não há nada a separar.
- `cron: '17 12 * * 1'` (segunda-feira, minuto/hora deslocados do topo da
  hora para evitar contenção) + `workflow_dispatch` manual.
- Permissões: `contents: read` (read-only), sem PR/merge automático.
- Escalada: o workflow **não pode ficar verde hoje** — `ty check` (150
  diagnósticos pré-existentes) e `bandit -r src` (3 findings pré-existentes)
  já falham no baseline atual, fora do escopo deste reparo. Isso é
  intencional e documentado em `known_risks`: o relatório fica como artefato
  (`weekly-testing-assessment-*.json`, `coverage.xml`, `junit.xml`), quem
  olha a aba Actions vê o X vermelho: **não é sinal de regressão nova**, é
  dívida pré-existente a ser tratada em esforço(s) separado(s)
  (`migracao-ty` para o `ty`; um novo mapa para o `bandit`). Sem
  notificação automática além do próprio Actions — read-only não permite
  outra coisa sem identidade de bot dedicada (fora de escopo aqui).
- Próxima objective semanal: ancorada no `next_objective` do `state.json` —
  hoje, triar os 34 skips.