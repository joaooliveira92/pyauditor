# 02 — Mecanismo do gate contra costura de strings

Type: grilling
Status: open
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