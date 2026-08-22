# 03 — Reparar as costuras de strings e deixar a suíte verde

Type: task
Status: open
Label: wayfinder:task

## Question

Executar o reparo das **~443 costuras de strings sem espaço** (53 arquivos entre `src/` e `tests/`) — uma regressão acidental introduzida pelo refactor em andamento, que hoje quebra 33 testes (padrão único: texto pt-BR colado, ex. `ASCIIpositivo`, `doCSV`, `NºSolicitação`).

Parâmetros definidos em charting (Q6/Q7/Q9):
- Mecânica: **script de uma passada** que restaura o espaço exatamente nas concatenações implícitas (o texto quebrado, ex. `'...ASCII'`+`'positivo, '` → `'...ASCII '`+`'positivo, '`), com revisão por diff antes de aplicar.
- Critérios de aceite:
  1. o diff contém **apenas** a inserção de espaços nas concatenações implícitas (nenhuma outra mudança semântica, nem refactor);
  2. `uv run --locked pytest` verde na árvore toda (hoje: 33 falhas, 526 passam, 34 skips);
  3. `uv run --locked ruff check` e `ruff format --check` limpos em `src` e `tests`;
  4. **commit separado** do refactor em andamento (Q9) — não mesclar.
- Casos legítimos de junção SEM espaço (ex. `'Nº'` + valor/cabeçalho de coluna que deve ficar colado em runtime) — NÃO reparar; listar em `notes/casos-intencionais.md` com a justificativa, como insumo para o ticket 02.
- Coordenação com o refactor: conferir `git diff` e `git status` antes de aplicar, trabalhar sobre a árvore atual sem afetar edições concorrentes.

Resolução: patch aplicado e verde, commit `fix: ...` separado, exceções documentadas, e o gist + link no map.