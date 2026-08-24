# Wire summary_json() warnings through server.py for run jobs

- **Status:** resolved
- **Type:** wayfinder:task

## Question

`src/ui/server.py::App.start_job`/`_collect` capturam o stdout do
subprocess do pipeline como texto cru; nada estruturado chega no browser.
Decisões do charting (não re-abrir):

- Escopo é só o comando `run` — comandos por etapa não têm resumo JSON
  (ver "Out of scope" do map).
- `build_command` passa a incluir `--output json` quando `command == "run"`
  (hoje nunca passa `--output`, default é `text` no CLI).
- Isso troca só o bloco final de resumo por uma linha JSON — o streaming ao
  vivo do log (stderr fundido em stdout) não muda, confirmado nas Notes do
  map.
- A UI só precisa da lista `warnings` do JSON, não do resumo completo
  (`indicadores`/`glosa`/`publicação` ficam de fora deste ticket).

Implementar: `Job` (dataclass) ganha um jeito de expor os warnings depois
que o processo termina — parsear a última linha não-vazia do output
acumulado como JSON, extrair `warnings`, guardar em `Job` (ou computar sob
demanda em `/api/pipeline/<id>`). Se o parse falhar (comando não era `run`,
saída não é JSON, processo falhou antes de imprimir o resumo) devolver
`warnings: []` sem quebrar a resposta existente — o output cru continua
disponível do jeito que já é hoje.

Carrega execução: implementar em `server.py` + testes em
`tests/test_ui_server.py` (processo real ou fake que imprime uma linha JSON
de resumo, cobrindo o caso de sucesso e o caso de saída não-JSON/comando
não-`run`).

## Answer

Implementado em `src/ui/server.py`:

- `build_command` acrescenta `--output json` sempre que `command == "run"`
  (não muda o streaming ao vivo — stderr continua fundido em stdout).
- `Job` ganhou o método `warnings()`: varre `self.output` de trás pra
  frente até achar a última linha não-vazia, tenta `json.loads` nela, e
  devolve `summary["warnings"]` se for uma lista; qualquer coisa que não
  bata esse formato (comando não-`run`, saída não-JSON, chave ausente)
  devolve `[]` sem lançar exceção.
- `GET /api/pipeline/<id>` agora inclui `"warnings": job.warnings()` na
  resposta, ao lado de `status`/`returncode`/`output` — nenhum contrato
  existente mudou.

Testes novos em `tests/test_ui_server.py`: dois testes de ponta a ponta
usando um "pipeline" fake (script Python descartável apontado por
`pipeline_template`) — um que imprime um resumo JSON com `warnings` (caso
`run`, sucesso) e um que imprime texto puro (caso não-`run`, sem JSON),
confirmando `warnings == [...]` e `warnings == []` respectivamente. Suite
completa (`uv run pytest`, 638 passed) e `ruff check`/`mypy` em
`src/ui/server.py` não introduzem erro novo — os que aparecem já existiam
antes desta mudança (confirmado com `git stash`), mesmo padrão de dívida
pré-existente documentado no ticket 01.
