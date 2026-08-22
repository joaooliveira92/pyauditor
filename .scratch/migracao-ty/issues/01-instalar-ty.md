# 01 — Instalar ty no ambiente

**Type:** task
**Status:** aberto
**Blocked by:** nenhum

## Question

Como o ty entra no ambiente da estação de trabalho e qual versão fica garantida?

-   Instalar globalmente via `uv tool install ty@latest` (decisão do usuário na sessão de charting — não é dependência do projeto).
-   Registrar a versão instalada e o comando de verificação (`ty --version`).
-   Nota: o passo de CI (ticket 06) e os agentes de research (ticket 02) podem usar `uvx ty` independentemente desta instalação — este ticket é sobre o ambiente local do human.

## Resolução

_(preencher ao resolver: versão instalada, saída de `ty --version`, qualquer peculiaridade do ambiente macOS evidenciada)_