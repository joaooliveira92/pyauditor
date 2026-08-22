# 03 — Endurecer supply-chain: ações por SHA + Dependabot

**What to build:** as dependências de CI deixam de ser frágeis. Todas as actions dos workflows passam a ser pinadas por commit SHA completo (com a tag de release mantida em comentário para legibilidade), e o Dependabot passa a manter GitHub Actions + lockfile do uv atualizados — cada atualização chega como PR, passando pelo gate de qualidade antes de entrar em `dev`.

**Blocked by:** nenhum — pode começar imediatamente.

**Status:** ready-for-agent

- [ ] Todas as actions de todos os workflows estão pinadas por SHA completo, com a tag em comentário.
- [ ] `dependabot.yml` configurado para GitHub Actions e para o ecossistema do uv (lockfile).
- [ ] Uma atualização de action/dependência gerada pelo Dependabot passa pela PR com o gate de qualidade verde.
- [x] O `docs.yml` não usa mais `pip install zensical` sem versão (instalação determinística).

## Resposta

Todas as actions de `quality.yml`, `weekly-testing.yml` e `pages-deploy.yml`
pinadas por SHA completo, tag no comentário (validado pelo script
`validate_workflow.py` da skill devops). `.github/dependabot.yml` criado para
GitHub Actions + ecossistema `uv`. O deploy de docs instalou o zensical via
`uv sync --locked --group docs` (versão resolvida do `uv.lock`, não
`pip install zensical` solto).

Status: resolved