# 01 — Instalar ty no ambiente

**Type:** task
**Status:** resolvido
**Blocked by:** nenhum

## Question

Como o ty entra no ambiente da estação de trabalho e qual versão fica garantida?

-   Instalar globalmente via `uv tool install ty@latest` (decisão do usuário na sessão de charting — não é dependência do projeto).
-   Registrar a versão instalada e o comando de verificação (`ty --version`).
-   Nota: o passo de CI (ticket 06) e os agentes de research (ticket 02) podem usar `uvx ty` independentemente desta instalação — este ticket é sobre o ambiente local do human.

## Resolução

-   Instalado globalmente via `uv tool install ty@latest` (confirma `uv tool list`: `ty v0.0.73`).
-   `ty --version` → `ty 0.0.73 (4bd2833c4 2026-08-18)`.
-   `uvx ty@0.0.73` também resolve e roda o check no repo (`uvx ty@0.0.73 check src` → `All checks passed!`) — sem poluir o projeto.
-   Fato ambiental macOS evidenciado: nenhum peculiar — binário em `~/.local/bin/ty` (dir padrão do `uv tool`), já no PATH.
-   O CI (ticket 06) e o `weekly-testing.yml` usam `uvx ty@0.0.73` pinado, independente desta instalação local.