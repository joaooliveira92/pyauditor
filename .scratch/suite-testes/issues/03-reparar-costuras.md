# 03 — Reparar as costuras de strings e deixar a suíte verde

Type: task
Status: resolved
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

## Answer

Na árvore atual (após o commit `wip: fixing test suite`, que já corrigira parte da regressão), restavam 16 testes falhando, não 33 — mas a causa era a mesma costura de string. Em vez de um único script automático de substituição, o reparo foi feito por três varreduras complementares seguidas de correção manual revisada por arquivo (o script de fronteira sozinho teria perdido ~10 casos):

1. **Varredura por fronteira de concatenação implícita** (script `tokenize`-based, decodifica `FSTRING_MIDDLE` incluindo escapes `\n`/`\t` e chaves `{{`/`}}`): comparou o último caractere de um literal com o primeiro do literal seguinte, sinalizando quando ambos são caracteres de palavra (incl. acentuação pt-BR) sem espaço entre eles. Achou 79 costuras em `src/` e `tests/`.
2. **Varredura por transição de caixa dentro de um único literal** (regex `MAIÚSCULAS+minúscula` e `minúscula+MAIÚSCULAS`): pegou casos onde o `ruff format` já havia fundido os dois literais quebrados em um só, "eternizando" o bug e escondendo-o da varredura 1 (ex.: `f"falhaaoler{equipe_path}:{exc}—responsáveisficam'[apreencher]'"` em `excel/equipe.py`). Achou ~10 casos reais entre 190 candidatos (o resto era ruído: `MinC`/`MTur`/`CSVs`/`OSError` etc.).
3. **Triagem dos testes que ainda falhavam após 1+2**: revelou 3 costuras que nenhuma varredura estática pegou — chaves de dicionário totalmente em minúsculas sem transição de caixa (`"Fiscalrequisitante"`, `"Fiscaladministrativo"`, `"Gestordocontrato"` em `rom/render.py`, usadas para indexar `capa_fields` e por isso quebrando o lookup, não só a exibição) e uma mensagem de erro (`WRITE_FAILURE_HINT` em `cli/results.py`) que era um único literal sem nenhum espaço.

Nenhum caso legítimo de colagem intencional foi encontrado (ver `notes/casos-intencionais.md`) — o ticket 02 não precisa de `per-file-ignores` motivado por este levantamento.

Critérios de aceite:
1. Diff contém só inserção de espaços (e o rewrap de linhas que passaram de 80 colunas por causa do espaço extra, sem mudar o texto) — nenhuma outra mudança semântica.
2. `uv run --locked pytest`: **559 passed, 34 skipped** (era 16 failed / 543 passed antes deste ticket).
3. `uv run --locked ruff check src tests`: 16 erros, idênticos ao baseline pré-existente (nenhum introduzido). `uv run --locked ruff format --check src tests`: 2 arquivos não formatados, idênticos ao baseline pré-existente.
4. Commit separado do refactor em andamento (a fazer a seguir).