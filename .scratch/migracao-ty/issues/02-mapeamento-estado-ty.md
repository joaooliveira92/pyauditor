# 02 — Mapear o estado do ty sobre o repo

**Type:** research
**Status:** resolvido
**Blocked by:** nenhum

## Question

Antes de escrever qualquer `[tool.ty.*]` config, precisamos saber o que o ty "de fábrica" (defaults, sem config no pyproject) diz desta base hoje. Isso dimensiona o trabalho e informa o perfil estrito do ticket 03.

Entregue 3 fatos:

1.  **Mapa dos 32 suppressions atuais**: para cada `# type: ignore[...]` em `src/` e `tests/` (códigos mypy: `arg-type`, `no-untyped-call`, `assignment`, etc. — ver listagem no mapa), qual a **regra ty correspondente** (`# ty: ignore[<rule>]`) ou, se a regra não tiver equivalente, qual comportamento o ty teria ali (supressão via `respect-type-ignore-comments`? simplesmente necessário mexer no tipo?).
2.  **Délta de diagnostics**: rodando ty com defaults sobre `src` + `tests`, catalogar diagnostics por módulo e por regra — o que aparece que com basedpyright strict (atual limpo) não aparece. Separar: (a) dívida real de tipagem; (b) ruído de stubs de terceiros (`types-openpyxl`, `types-pyyaml`, `questionary`, `rich`, `loguru`).
3.  **Strict-equality/analysis**: o que o default do ty assume que poderia surpreender (narrowing por ==), e se as flags `[tool.ty.analysis]` (`strict-equality-semantics`, `strict-generic-narrowing`) são relevantes para este repo.

Ferramenta (uma das formas, sem poluir o projeto): `uvx ty check .` — se `uvx ty` não disponível, consulte a doc do CLI do ty; pode usar o próprio executável global se já instalado (ticket 01). **Não altere arquivos de `src/`/`tests/`** durante o research — é leitura pura. Grave os achados em um arquivo `notes/estado-ty.md` sob `.scratch/migracao-ty/` e aponte-o aqui.

## Resolução

Nota completa: `.scratch/migracao-ty/notes/estado-ty.md` (ty 0.0.73; baseline basedpyright strict = `0 errors`).

1.  **Mapa dos 32 suppresses:** `# type: ignore[<código mypy>]` **não suprime nada no ty** (códigos sem prefixo `ty:` são ignorados; confirmado empiricamente em capa.py:136). `arg-type`→`invalid-argument-type`, `assignment`→`invalid-assignment`, `return-value`→`invalid-return-type`, `misc`→`invalid-assignment` (read-only), `index`→`invalid-assignment` (subscript), `dict-item`→`invalid-argument-type`. **Sem equivalente:** `no-untyped-call` (6), `no-untyped-def` (3), `call-arg` (1) e um `assignment` (split.py:338) — **11 comments mortos**, removíveis; 21 sites geram diagnóstico e exigem migração `# ty: ignore[...]`.
2.  **Delta:** **150 diagnostics** (src 3 + tests 147) = `invalid-argument-type` 133, `invalid-assignment` 5, `invalid-return-type` 1, `unsupported-operator` 8, `no-matching-overload` 3. Classificação: **(a)** 139 de dívida de tipagem real (grosso = `write_sheet(**kwargs)` nos testes: 12–17 diag por linha por overload); **(b)** 11 de ruído de stub `types-openpyxl` (`cell.row: int | None` via `MergedCell` → `+`/`sheet.cell`) — todos novos, sem `# type: ignore` prévio. Nenhum diagnóstico de `unresolved-import`; todas as libs resolvem no `.venv`.
3.  **Analysis/equality:** repo usa narrowing por `==`/`in` sobre `Literal`/`str` (status, commands), sem `match`-statements. Medido: `strict-equality-semantics=true` → delta 0; `strict-generic-narrowing=true` → +26 diag (14 `not-subscriptable` + 7 `unresolved-attribute`). Recomendação pro ticket 03: manter ambas `false`.

Fato rápido: ty **não cria** cache `.ty/` no repo (nada a adicionar no `.gitignore`); `openpyxl`/`pyyaml` sem `py.typed` são resolvidas pelos stubs `types-*` do `.venv`; CLI é `uvx ty check <caminhos>`.

**Status:** resolvido