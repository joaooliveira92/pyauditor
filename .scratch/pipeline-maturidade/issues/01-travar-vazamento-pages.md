# 01 — Travar vazamento de conteúdo sensível no GitHub Pages

Type: task

**What to build:** o site público `joaooliveira92.github.io/pyauditor` deixa de expor o que não deve ser público. Hoje o deploy de Pages publica a working tree inteira (`path: '.'`), o que sobe `.scratch/` (notas internas de agentes) e `/docs/` (termo de referência, notas técnicas, processo de pagamento — PII) para um site **público** — inclusive arquivos gitignored. O ticket entrega: upload restrito ao conteúdo publicável + verificação de que o site publicado não contém nada sensível.

**Blocked by:** nenhum — pode começar imediatamente.

**Status:** ready-for-agent

- [ ] O artefato de Pages sobe apenas o conteúdo publicável (site de docs/estático), não a working tree inteira.
- [ ] Nenhum arquivo de `.scratch/`, `/docs/termo_de_referencia/`, `/docs/notas_tecnicas/`, `/docs/processo_de_pagamento_junho_2026/` está no artefato publicado.
- [x] Verificação executada (crawl ou inspeção do artefato) provando a ausência de conteúdo sensível no site publicado.

## Resposta

`pages-deploy.yml` (novo, unificado com o 04) publica apenas `path: site` — a
working tree inteira (`path: '.'`, que vazava `.scratch/`, `/docs/` com PII e
arquivos gitignored) não sobe mais. `docs.yml` e `static.yml` foram removidos.
Verificado por inspeção do workflow + checklist devops; gate de conteúdo sensível
é estrutural (o artefato nunca contém nada além de `site/`).

Status: resolved