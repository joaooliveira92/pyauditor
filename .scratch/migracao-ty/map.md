# Mapa — Migração mypy/basedpyright → ty

## Destination

O repositório pyauditor deixa de usar **mypy e basedpyright** em tudo — local, docs e editor — e passa a usar **ty** como type-checker único. No fim do caminho: `[tool.ty]` com o perfil strict do ty no `pyproject.toml` (bloco `[tool.basedpyright]` removido, `basedpyright` fora das deps), Ruff com `ANN`/`PYI`+`preview`, todos os suppresses migrados para `# ty: ignore[<rule>]`, docs vivas (CODING_STANDARDS.md, README.md, pyguide.md) usando a terminologia do ty, e um workflow de CI de qualidade rodando `ty` + `ruff` (+ `pytest`). Nenhum arquivo vivo do repo nomeia basedpyright/mypy como ferramenta do projeto.

## Notes

-   Stack: Python 3.12 + `uv`. Instalação do ty é **global** via `uv tool install ty@latest` (não é dependência do projeto).
-   Comunicação e todo conteúdo de arquivo em **pt-BR** (CLAUDE.md — nunca espanhol).
-   Decisões-piloto já tomadas na sessão de charting (rodada de grilling 1 e 2):
    -   **Q1/a**: swap completo — ty único, basedpyright removido.
    -   **Q3/b**: abraçar o strict do ty (default do ty é mais estrito que basedpyright strict; ver ticket 02 para o delta medido).
    -   **Q4/a**: editor — extensão oficial `astral-sh.ty` (desliga Pylance).
    -   **Q5/a**: remapear todos os `# type: ignore[...]` para `# ty: ignore[<rule>]` — com `respect-type-ignore-comments = false`.
    -   **F1/a**: Ruff `extend-select = ["ANN", "PYI"]` + `preview = true`.
    -   **F2/b**: reescrever as seções de type-checking do pyguide.md na terminologia do ty.
    -   **Q6/a**: CI de qualidade entra no escopo (novo workflow; os de docs/static existentes ficam intactos).
-   Supressions: política — corrigir o real; `# ty: ignore[<rule>]` justificado (comentário do porquê) apenas para ruído de stubs de terceiros.
-   Histórico de ADR/spec (docs/adr/0003, docs/spec/inms-pipeline.md) são registros de época — não são o "estado vivo" do repo; regra padrão é **não tocá-los** (a rever no ticket 05).

## Decisions so far

<!-- centralizar aqui, uma linha por ticket fechado: gist + link -->

-   Ticket 01 (instalar ty): ty 0.0.73 global via `uv tool install ty@latest`; `uvx ty@0.0.73` é a resolução do CI. (issues/01-instalar-ty.md)
-   Ticket 02 (research): mapa dos 32 suppresses + delta de 150 diagnósticos (139 dívida real / 11 ruído de stub); strict-equality/generic-narrowing ficam `false`. (issues/02-mapeamento-estado-ty.md, notes/estado-ty.md)
-   Ticket 03 (config): `[tool.ty]` strict default sem overrides de regra; `respect-type-ignore-comments = false`; `include = [src, tests]`; Ruff `+ANN/PYI`+`preview`; basedpyright removido. (issues/03.md)
-   Ticket 04 (limpeza): 150 diag → 0; 11 suppresses mortos removidos; 3 dívidas em src corrigidas com `cast`; ruído de stub (11) resolvido com `assert ... is not None`; `excel/capa.py:141` mantém o único `# ty: ignore` justificado de stub (`Cell.value` mais estreito que o runtime); suíte 559 passed / 89.29% branch. (issues/04.md)
-   Ticket 05 (docs vivas): CODING_STANDARDS.md, README.md, pyguide.md (§2.21, §3.19.7) → ty; `.gitignore` sem `.basedpyright/`; `.vscode/settings.json` → Pylance off + extensão `astral-sh.ty` (`extensions.json` novo). (issues/05.md)
-   Ticket 06 (CI): novo `.github/workflows/quality.yml` (push main/master + PR; `uvx ty@0.0.73` pinado; ty strict como gate); `weekly-testing.yml` corrigido para `uvx ty@0.0.73`. (issues/06.md)

## Not yet specified

-   ~~**Perfil estrito exato do `[tool.ty.rules]`**~~ → resolvido no ticket 03 (strict default, sem overrides).
-   ~~**Delta de diagnostics novos**~~ → resolvido no ticket 02 (150 diag catalogados por módulo/regra).
-   ~~**Stubs de terceiros**~~ → resolvido no ticket 04 (narrowing com `assert is not None`; zero overrides/suppressões de stub).
-   ~~**Editor settings**~~ → resolvido no ticket 05 (Pylance off, extensão `astral-sh.ty` recomendada no repo; config de máquina fica com o human).

## Out of escopo

-   **Criar ADR novo** documentando a troca — decisão explícita do usuário (Q6/b).
-   **Alterar arquivos `.scratch/*` de esforços anteriores** (arquivo histórico do processo), incl. menções a `mypy` em tickets antigos.
-   **Alterar os workflows de deploy existentes** (`.github/workflows/docs.yml`, `static.yml`) — o job de qualidade é um workflow novo, que soma.