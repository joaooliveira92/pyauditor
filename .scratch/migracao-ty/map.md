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

_(nenhum ticket fechado ainda)_

## Not yet specified

-   **Perfil estrito exato do `[tool.ty.rules]`**: a preocupação é espelhar "strict", mas o delta do default do ty sobre este repo ainda não foi medido — o ticket 02 (research) o resolve e gradua a configuração.
-   **Delta de diagnostics novos**: quais diagnostics o ty levanta que o basedpyright strict não levantava (por módulo/regra); o volume materializa o trabalho do ticket 04.
-   **Stubs de terceiros**: `types-openpyxl`, `types-pyyaml`, stubs de `questionary`/`rich`/`loguru` — como o ty as resolve; pode exigir `overrides`, `allowed-unresolved-imports`, `replace-imports-with-any` ou downgrades de regra em `[tool.ty.overrides]`.
-   **Editor settings**: o `.vscode/settings.json` hoje só liga Pylance `full` — precisa da extensão `astral-sh.ty` e o comportamento `python.languageServer` (o config em repo vs máquina está por decidir).

## Out of escopo

-   **Criar ADR novo** documentando a troca — decisão explícita do usuário (Q6/b).
-   **Alterar arquivos `.scratch/*` de esforços anteriores** (arquivo histórico do processo), incl. menções a `mypy` em tickets antigos.
-   **Alterar os workflows de deploy existentes** (`.github/workflows/docs.yml`, `static.yml`) — o job de qualidade é um workflow novo, que soma.