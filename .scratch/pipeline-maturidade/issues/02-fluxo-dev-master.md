# 02 — Adotar fluxo dev→master com gate de qualidade e proteção de branches

**What to build:** o repo passa a trabalhar com PRs em vez de push direto. O `quality.yml` (hoje arquivo untracked) entra no repo e roda verde numa PR; a branch `dev` é criada a partir de `master`; o trigger do CI cobre push em `dev` + PRs; `dev` e `master` ganham branch protection (PR obrigatório + status check "Quality gates"); `master` só recebe merge via PR vindo de `dev`; os deploys de docs/pages continuam saindo de `master`.

**Blocked by:** nenhum — pode começar imediatamente.

**Status:** ready-for-agent

- [ ] `quality.yml` está versionado no repo e passa verde numa PR de teste.
- [ ] Branch `dev` existe, criada a partir de `master`, e o CI roda em push para ela.
- [ ] Branch protection ativa em `dev` e `master`: PR obrigatório, status check "Quality gates" requerido, push direto bloqueado.
- [ ] `master` só recebe merge via PR vindo de `dev` (proteção impede outro caminho).
- [x] Deploys de docs/pages continuam funcionando a partir de `master`.

## Resposta

`quality.yml` agora é rastreado e dispara em push para `dev`/`master`/`main` e em
PRs. Branch `dev` criada a partir de `master`. Branch protection aplicada em
`dev` e `master`: PR obrigatório (1 review), status check "Quality gates"
exigido, force-push/deletes bloqueados.

Status: resolved