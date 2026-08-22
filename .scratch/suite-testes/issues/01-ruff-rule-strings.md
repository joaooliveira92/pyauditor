# 01 — Que regra do Ruff detecta concatenação implícita de strings?

Type: research
Status: resolved
Label: wayfinder:research

## Question

Qual regra do Ruff (nome, versão, estado estável/preview) detecta concatenação implícita de literais de strings adjacentes — dois literais de string colados, sem operador, com ou sem espaço — a ponto de servir de **gate anti-re-regressão** das ~443 "costuras sem espaço" (ex. `'...ASCII'` + `'positivo, '` → `ASCIIpositivo`) introduzidas acidentalmente neste repo?

Incluir:
1. Nome da regra / família (ex. `ISC`, `RUF`, outra) e se está atrás de `preview`.
2. Se cobre o caso "sem espaço" (texto colado) vs apenas "concatenção implícita sem `+`"; como é o `noqa`/`.gitattribute` para junção legítima.
3. Interação com `ruff format` (que hoje é gate de CI): `ruff format` une ou separa strings adjacentes? `--check` sinaliza?
4. Config minimum para `[tool.ruff.lint]` (com `preview = true`, select já existente AN extensivo) + `per-file-ignores` para casos intencionais.
5. Verdict expresso: regra do Ruff vs custom AST-lint em pytest — pontos do docs que sustentem a escolha.

Fonte: documentos primários do Ruff (docs.astral.sh/ruff). Findings registradas em `.scratch/suite-testes/notes/ruff-rule-strings.md`. O resultado alimenta a decisão do ticket 02.

## Answer

**Usar a família `ISC` do Ruff como gate** — não um driver custom em pytest.

- Regra estável (`ISC001`/`ISC002`/`ISC003` desde v0.0.201; compatível com `ruff>=0.12` do repo), nenhuma sob `preview`; `ISC004` é extra desde 0.16 (default ligado, ortogonal).
- Cobre o caso "sem espaço": `ISC001` (uma linha), `ISC003` (com `+`), e `ISC002` + `allow-multiline = false` (duas linhas entre parênteses — o padrão exato das 443 costuras). Não existe opção "exigir separação" — casos legítimos via `# noqa`/`per-file-ignores`.
- Formatter: `ruff format` **funde** dois literais adjacentes quando o texto cabe em 80 cols (apaga a quebra). Proteção dupla: costuras pequenas auto-fundidas; a forma multilinha longa é preservada e o `ISC002` estrito a sinaliza no `check`.
- Snippet recomendado: `extend-select = ["ISC001","ISC002","ISC003"]` + `[tool.ruff.lint.flake8-implicit-str-concat] allow-multiline = false` (efeito colateral: `ISC003` auto-desabilitado). **Limpar as 443 costuras antes de ligar** (senão o diff inteiro explode no CI).
- Formatter é o fator: lint e format rodam no mesmo AST; o driver custom veria texto já reescrito (visão em stale) — sem ganho. Detalhe completo em `notes/ruff-rule-strings.md`.