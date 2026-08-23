# 03 — Rede de testes de versionamento do pipeline e de resolução de fonte

**What to build:** testes unitários para os dois pontos de produção menos cobertos hoje: a função de versão do pipeline (único módulo com subprocess, três caminhos: pacote instalado, commit git, marcador fixo) e a decisão de resolução de fonte (ramo manifest com delimiter divergente por arquivo, ramo de CSV legado, erro de manifest ausente e o ponto de chamada que decide entre `encoding`/`delimiter` configurados e detectados). O comportamento dependente de ambiente é testado com mock; a decisão do chamador — não apenas a função pura isolada — fica coberta, que é onde o problema de produção (delimiter divergente por arquivo) realmente mora.

**Blocked by:** nenhum — pode começar imediatamente.

**Status:** ready-for-agent

- [ ] `pipeline_version` testa os três caminhos (pacote instalado via metadata, commit via subprocess mockado, fallback fixo quando ambos falham) sem depender do estado real do ambiente.
- [ ] A resolução de fonte testa: ramo dataset via manifest, ramo CSV legado, manifest ausente com `dataset` declarado → erro acionável.
- [ ] O delimiter divergente é testado no ponto de decisão do chamador (troca pelo detectado quando o configurado não aparece no cabeçalho — e o mutismo quando não há candidato).
- [ ] `uv run pytest`, `uv run ty check` e `uv run ruff check` verdes; cobertura não cai.

## Contexto (do relatório de fricção)

`pipeline_version` roda `subprocess` com timeout de 5s e é o módulo sem nenhum teste; `resolve_source` é testado só por integração. A função de detecção de delimiter já tem teste isolado, mas a decisão do chamador (que foi fato de produção em 2026-06) não.