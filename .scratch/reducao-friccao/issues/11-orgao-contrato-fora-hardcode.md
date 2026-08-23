# 11 — Órgão e contrato fora do hardcode

**What to build:** o conhecimento de negócio hoje embutido no código — o mapa de órgão → contrato (usado na injeção de órgão das configs single-source) e o contrato default da config — passa a ser um dado central único (tabela de referência carregada de um só lugar), consumido pela descoberta de configs e pelo modelo de config. Nenhum comportamento muda: só deixa de ser necessário editar código para trocar o texto de um contrato.

**Blocked by:** nenhum — pode começar imediatamente.

**Status:** ready-for-agent

- [ ] Nenhum texto de contrato (nem o mapa órgão→contrato) fica hardcoded no código; a fonte única é consumida pela injeção de órgão e pelo default da config.
- [ ] Comportamento idêntico ao de hoje para MinC e MTur (mesmos contratos injetados) — coberto por teste.
- [ ] Alterar o contrato de um órgão não exige editar código (só o dado).
- [ ] `uv run pytest`, `uv run ty check` e `uv run ruff check` verdes; cobertura não cai.

## Contexto (do relatório de fricção)

O discovery embute o mapa `MinC/MTur → '40/2022 - …'` e o modelo de config carrega o contrato default hardcoded — conhecimento de negócio no código, e o universo de órgãos aparece no modelo como `Literal['MinC','MTur']`.