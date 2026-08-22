# 02 — Mecanismo do gate contra costura de strings

Type: grilling
Status: resolved
Label: wayfinder:grilling
Blocked by: 01

## Question

Com o mapeamento do ticket 01 (regra `ISC` do Ruff, estável, sem preview), decidir **a forma do gate que impede a reintrodução das "costuras de strings sem espaço"**:

- (a) habilitar `ISC001`/`ISC002`/`ISC003` no `[tool.ruff.lint]` com `allow-multiline = false`, (b) gate custom em pytest (AST), ou (c) híbrido. O ticket 01 recomenda (a) — validar se o usuário confirma contra a perda do `ISC003` (`allow-multiline = false` auto-desabilita o `+`) ou prefere o pacote alternativo.
- Qual padrão proibir: a concatenação implícita de literais inteira, ou apenas o caso "sem espaço" (texto pt-BR colado)?
- Como acomodar os casos intencionais (ex. `'Nº'` + valor de coluna em runtime) — `per-file-ignores` vs `# noqa: ISC001` inline vs refactor para f-string.
- Onde o gate deve rodar (CI de qualidade/tests) e a relação com o workflow que o `migracao-ty` já planeja — sem duplicar execução.
- Ordem: **limpar as 443 costuras primeiro (ticket 03) e só então ligar o gate** — o `ruff check` explodiria no diff inteiro caso contrário.

Resolução: `## Answer` + fechamento + contexto no map.

## Answer

**Gate = `ISC001` + `ISC003` no `[tool.ruff.lint]`, sem `allow-multiline = false`.**

- `extend-select = ["ANN", "PYI", "ISC001", "ISC003"]`, sem seção
  `[tool.ruff.lint.flake8-implicit-str-concat]` — ISC002 (multi-linha) fica
  de fora.
- Motivo da revisão frente à recomendação do ticket 01: rodar
  `ruff check --select ISC002` com `allow-multiline = false` no código real
  gerou **746 erros** (569 em `src`, 177 em `tests`), quase todos costuras
  **legítimas e corretamente espaçadas** — o repo constrói f-strings e
  tabelas Markdown deliberadamente em várias linhas (ex.
  `src/pyauditor/rom/render.py`, 125 hits). O `notes/casos-intencionais.md`
  do ticket 03 só cobriu as ~90 costuras já encontradas por varredura
  dirigida, não a superfície completa que `ISC002` estrito passa a cobrir —
  não é evidência de que o rigor multi-linha esteja limpo.
- `ISC001`/`ISC003` (concatenação implícita/explícita numa única linha) têm
  **0 hits** no código atual — gate limpo, sem `per-file-ignores` adicional,
  e cobrem o formato mais comum de erro de digitação (colagem na mesma
  linha). Não isolam perfeitamente o padrão exato da regressão original
  (que era multi-linha) porque o Ruff não tem opção "exigir espaço na
  junção", só "proibir junção" — ticket 01 já registrava essa lacuna.
- Acomodação de casos intencionais: não necessária agora (0 hits); se um
  `ISC001`/`ISC003` real e intencional aparecer no futuro, resolver com
  `# noqa: ISC001` inline (não `per-file-ignores`, para não apagar sinal do
  arquivo inteiro).
- Onde roda: `ruff check` já é gate de CI existente (mesmo comando do
  workflow de qualidade) — nenhum workflow novo necessário para o gate em
  si; a integração com o ciclo semanal fica para o ticket 04.
- Validado: `ruff check src tests` e `ruff format --check src tests`
  produzem exatamente os mesmos 18 erros / 3 arquivos pré-existentes de
  antes da mudança (confirmado via `git stash`) — nenhuma regressão. Suíte
  completa segue verde: 559 passed / 34 skipped, cobertura 89.28%.