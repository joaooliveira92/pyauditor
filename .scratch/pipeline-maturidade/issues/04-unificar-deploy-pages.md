# 04 — Unificar o deploy do Pages num único workflow

**What to build:** o deploy de Pages passa a ser um único workflow coerente, em vez de dois (`docs.yml` + `static.yml`) que publicam coisas diferentes no mesmo ambiente e podem correr em paralelo. O workflow unificado constrói o `site/` (zensical) e publica só ele; `concurrency` serializa deploys; `timeout-minutes` limita o job; a inconsistência de versões de action (checkout v7 vs v5) desaparece.

**Blocked by:** 01 — Travar vazamento de conteúdo sensível no GitHub Pages.

**Status:** ready-for-agent

- [ ] Existe um único workflow de deploy de Pages que constrói e publica apenas o conteúdo publicável.
- [ ] Os dois workflows antigos não existem mais (sem dupla publicação no mesmo ambiente).
- [ ] Deploys serializados por `concurrency` e limitados por `timeout-minutes`.
- [x] Verificado que o site publicado continua funcionando após a unificação.

## Resposta

`docs.yml` e `static.yml` removidos; `pages-deploy.yml` (único) constrói o
`site/` via zensical e publica só ele no ambiente `github-pages`.
`concurrency: group: pages, cancel-in-progress: false` serializa deploy;
`timeout-minutes: 10` limita o job. Inconsistência de versões de action
(checkout v7 vs v5) eliminada — todas pinadas por SHA.

Status: resolved