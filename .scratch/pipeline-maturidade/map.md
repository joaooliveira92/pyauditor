# Map: pyauditor — maturidade do pipeline de gestão de código

Label: wayfinder:map

## Destination

Elevar a maturidade do pipeline de gestão de código (commits, push, actions) do estado atual — CI básico sem proteção de revisão nem supply-chain — para um pipeline seguro, reproduzível e observável: sem vazamento de conteúdo sensível no site público, fluxo de PRs dev→master com gate de qualidade obrigatório, dependências de CI pinadas e atualizadas por Dependabot, deploy de Pages unificado, falhas do ciclo semanal virando issues e compatibilidade de runtime provada em matriz.

## Notes

- **Contexto atual (medido, agosto/2026)**: `quality.yml` existe mas está **untracked** (gate não está ao vivo); master **sem branch protection** (API 404); `static.yml` publica `path: '.'` — a working tree inteira num site público (inclui `.scratch/` e `/docs/` com PII, até gitignored); actions pinadas por tag móvel (v5/v6/v7); `docs.yml` instala `zensical` sem versão; docs.yml e static.yml publicam no mesmo `environment: github-pages` sem `concurrency` conjunto; nenhum Dependabot; sem release/publicação; sem hooks locais.
- **Decisões do usuário nesta sessão**: rejeitado qualquer pre-commit hook e validação de mensagem de commit; adotada a ideia de **branch `dev`** — o fluxo passa a ser feature → PR → `dev` → PR → `master`, com deploys saindo de `master`.
- **Domínio/vocabulário**: qualidade (ruff, ty, pytest), supply-chain (pinning por SHA, Dependabot), Pages (docs zensical + site público), branches (dev, master, branch protection, status check), semanal (cron de testes, issue no tracker).
- **Convenções do repo**: conteúdo em pt-BR (nunca espanhol); tracker local de issues em `.scratch/<feature>/issues/`; todos os workflows com `permissions` mínimas e `concurrency`.
- **Skill de referência**: `devops-python-github-actions` (baseline de CI, release, segurança).

## Decisions so far

<!-- o índice — uma linha por ticket fechado -->

-   [x] Ticket 01: restrict upload do Pages ao publicável; verificar ausência de conteúdo sensível. (issues/01-travar-vazamento-pages.md)
-   [x] Ticket 02: committar `quality.yml`; criar `dev` a partir de `master`; CI cobre push em `dev` + PRs; branch protection em `dev` e `master` (PR + status check "Quality gates"); `master` só via PR de `dev`. (issues/02-fluxo-dev-master.md)
-   [x] Ticket 03: actions pinadas por SHA (tag em comentário); Dependabot para GitHub Actions + uv; instalação determinística do zensical. (issues/03-supply-chain.md)
-   [x] Ticket 04: um único workflow de deploy de Pages (bloqueado por 01); `concurrency` serializa, `timeout-minutes` limita. (issues/04-unificar-deploy-pages.md)
-   [x] Ticket 05: falha do semanal cria issue no tracker (token `issues: write` no job); gate de cobertura explícito `--cov-fail-under=85`. (issues/05-falha-semanal-issue.md)
-   [x] Ticket 06: matriz Python 3.12/3.13 no `quality.yml` com `fail-fast: false`; mesmo status check na branch protection. (issues/06-matriz-python-313.md)

## Not yet specified

-   ~~Pre-commit hooks e validação de mensagem~~ → **rejeitados pelo usuário** (fora do escopo).

## Out of escopo

-   Release/pypi: projeto `0.1.0` ainda não publica wheel/sdist — futuro.
-   Pre-commit hooks e validação de mensagem de commit (decisão explícita do usuário).