# 04 — Operacionalizar o ciclo semanal de testes e coordenar o CI

Type: grilling
Status: open
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