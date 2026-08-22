# 05 — Falha semanal vira issue + gate de cobertura explícito

**What to build:** a saúde do repo deixa de depender de alguém olhar os logs do cron. Quando o ciclo semanal de testes falhar, um issue é criado no tracker (token com `issues: write`, apenas nesse job); o gate de cobertura passa a ser explícito no comando dos workflows (`--cov-fail-under=85`) em vez de depender só do `[tool.coverage.report]` do pyproject.

**Blocked by:** nenhum — pode começar imediatamente.

**Status:** ready-for-agent

- [ ] Uma falha no workflow semanal cria um issue no tracker com contexto suficiente (workflow, job, run id).
- [ ] O token usado no job semanal tem escopo mínimo (`issues: write` + `contents: read`), não o token de qualquer job.
- [x] Gate de cobertura explícito (`--cov-fail-under=85`) presente nos workflows que rodam pytest, sem depender só da config do pyproject.

## Resposta

`weekly-testing.yml` ganhou o passo "Create issue on failure" (`if: failure()`),
que cria issue via `gh` com workflow/job/run id/URL no corpo. O token do
workflow é explícito e mínimo: `contents: read` + `issues: write`. Gate de
cobertura `--cov-fail-under=85` adicionado aos comandos pytest de
`quality.yml` e `weekly-testing.yml`.

Status: resolved