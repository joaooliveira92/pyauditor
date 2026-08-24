# 05 — Plano de testes para `server.py`

- **Type:** grilling
- **Status:** resolved
- **Blocked by:** 02

## Question

`src/ui` não tem nenhum teste hoje. `server.py` já tem lógica sensível a
segurança (`resolve_file`: escape de workspace, extensões permitidas, limite
de 2 MiB) e vai ganhar superfície nova com a execução por etapa (ticket 02).

Resolver, depois que o ticket 02 define a forma nova do endpoint de pipeline:
o que testar (validação de path/extensão/tamanho, endpoints de arquivo,
endpoints de pipeline por etapa), que framework (stdlib `unittest` +
`http.client`, ou `pytest` como o resto do repo — ver `tests/`), e onde os
testes vivem (`tests/` na raiz junto do resto, ou `src/ui/tests/` próprio,
dado que hoje `src/ui` é copiado/distribuído separadamente do resto do
pipeline segundo o `README.md`).

## Answer

Grilled with the user; all three recommendations approved as-is.

1. **Escopo**: cobrir toda a superfície atual de `server.py` já nesta rodada
   — `resolve_file` (allowlist de sufixo, limite de 2 MiB, escape de
   workspace), `GET`/`PUT /api/file`, e `POST`/`GET`/`DELETE /api/pipeline`
   como existem hoje (template fixo `run`, `force`/`clean`/`competence`/
   `agency`). O campo `command` do ticket 02 chega depois como diff pequeno
   num teste existente, não como suíte nova.
2. **Framework**: `pytest` (já é dependência de dev na raiz — `hypothesis`/
   `pytest`/`pytest-cov`). A portabilidade de "copie `src/ui` pra qualquer
   lugar" é sobre *runtime*, não sobre onde os testes rodam — a suíte só
   roda a partir de um checkout completo do repo, onde `uv run pytest` já
   funciona; `unittest`+`http.client` só adicionaria boilerplate sem ganho
   real de portabilidade.
3. **Localização**: `tests/` na raiz (ex.: `tests/test_ui_server.py`), não
   `src/ui/tests/` próprio. `testpaths = ["tests"]` no `pyproject.toml` faz
   `uv run pytest` pegar o arquivo automaticamente; um diretório próprio
   dentro de `src/ui` ficaria invisível a um `pytest` default. Nada do que é
   copiado quando alguém distribui `src/ui` (`.py`/`.html`/`.css`/`.js`)
   inclui a pasta `tests/` da raiz, então nada da portabilidade é
   comprometido.
