Type: research
Status: resolved

## Question

`orchestration` (`run.py`, `state.py`) expõe `RunRequest`/`RunState`/resultados de execução consumidos tanto por `cli/main.py`/`cli/run.py` quanto pelo fluxo guiado em `interactive/flow.py`. Rastreie os dois lados: o que `cli` e `interactive` assumem sobre o estado/resultado que `orchestration` devolve sem revalidar (campos opcionais, códigos de saída, mensagens), e o que `orchestration` assume sobre o `RunRequest` que recebe de cada um dos dois entry points sem revalidar (ex.: `orgao`, `competencia`, listas de comandos vazias). Onde os dois entry points (`cli` direto vs. `interactive`) podem produzir um `RunRequest` de shape diferente que `orchestration` trata de forma inconsistente?

Registre também fricção concreta do modelo CSV+YAML nesta fronteira, se houver.

Aplique o skill `python-production-engineer` (ler `.agents/skills/python-production-engineer/SKILL.md` por inteiro) para julgar severidade. Achados citam `file:line`.

## Answer

Rastreados os dois lados da fronteira: `orchestration/run.py` (`RunRequest`/`RunResult`/`execute_run`/`_dispatch`/`_capa_path_for`), `orchestration/state.py` (`RunState`/persistência), `orchestration/summary.py` (`render_summary`/`exit_code_for_run`, consumido por ambos os entry points), `cli/main.py` (parsing argparse + `_dispatch_run`/`_dispatch_bootstrap`/etc.), `cli/run.py` (`run_run`, único ponto que monta `RunRequest` no lado CLI direto) e `interactive/flow.py`+`interactive/provider.py` (único ponto que monta `RunRequest` no lado guiado).

### P1 — `_capa_path_for` duplicado com lógica divergente entre `cli/main.py` e `orchestration/run.py`

`cli/main.py:373-379` e `orchestration/run.py:102-108` implementam a mesma operação conceitual ("caminho da capa por órgão, ao lado da capa comum") com regras diferentes:

- `cli/main.py::_capa_path_for` (usado por `_dispatch_bootstrap`/`_dispatch_measure`/etc., subcomandos diretos): para `orgao != "both"`, **sempre** descarta o nome de arquivo passado em `--capa-path` e devolve `capa_path.parent / f"capa_{orgao}.csv"` — não existe caminho de escape para um `--capa-path` customizado quando o órgão é único.
- `orchestration/run.py::_capa_path_for` (usado por `execute_run`/`_dispatch`, ou seja, `pyauditor run` e o fluxo interativo): se `capa_path.name != "capa.csv"` e `orgao != "both"`, devolve `capa_path` **como está** — a docstring até documenta a intenção ("An explicit non-default `capa_path` … wins as-is").

Consequência concreta: `pyauditor bootstrap --orgao MinC --capa-path meucapa.csv` grava em `capa_MinC.csv` (nome customizado ignorado), enquanto `pyauditor run --orgao MinC --capa-path meucapa.csv` (ou o mesmo fluxo via interativo) usa `meucapa.csv` literalmente. Mesmos flags, dois entry points, dois arquivos diferentes lidos/gravados — silenciosamente, sem erro ou aviso. Isso é exatamente o tipo de "RunRequest de shape equivalente tratado de forma inconsistente" que a pergunta do ticket busca, só que a inconsistência está na função auxiliar duplicada, não no dataclass em si.

Sugestão (sem implementar): eliminar a duplicação — mover uma única `_capa_path_for` para um módulo compartilhado (ex. `pyauditor.config` ou o próprio `orchestration.run`, importado por `cli/main.py`) e decidir qual das duas semânticas é a correta antes de unificar (a de `orchestration/run.py` parece a intencional, dado o comentário explícito).

### P1 — Resumo de execução no modo interativo pode mostrar `publicable`/`glosa calculada` como default falso-positivo em resume

`cli/run.py:56-58` sempre passa `force_commands=frozenset({"report", "consolidate"})` ao montar `RunRequest`, garantindo que essas duas etapas sejam redespachadas mesmo se já `done` num estado persistido — comentário em `cli/run.py:11-18` explica que isso é necessário "since they're cheap to regenerate... and the completion summary needs a fresh Result".

`interactive/flow.py:154-163` monta `RunRequest` sem passar `force_commands` — fica no default `frozenset()` de `orchestration/run.py:69`. Em modo interativo, se `report`/`consolidate` (ou `measure`) já estavam `done` num estado anterior e o usuário não marcou `--force`-equivalente (não existe essa opção no fluxo guiado — ver próximo achado), `execute_run` (`orchestration/run.py:311-318`, `continue` sem adicionar a `results`) pula o dispatch e **não gera nenhum `CommandResult` novo** para essas etapas nesta invocação.

`orchestration/summary.py::_sumario_orgao` (linhas 180-206) então não encontra `ReportResult`/`MeasureResult` correspondente via `_result_for_command` e cai no ramo `else` (linhas 189-192): `aferidos = 0` (ou o que sobrar de measure), `publicable = True`, `glosa_calc = True` — **defaults otimistas fixos**, não derivados de nenhum dado real desta execução. `exit_code_for_run` (`orchestration/summary.py:43-69`) também só enxerga `results` desta invocação, então nunca aciona código `4` (glosa não calculada) para uma etapa pulada por resume. O painel final mostra "Publicação: liberada" mesmo que a etapa `report` real desse órgão nunca tenha rodado nesta sessão.

Sugestão: dar ao fluxo interativo o mesmo `force_commands={"report", "consolidate"}` que `cli/run.py` usa (ou explicitar a divergência perguntando ao usuário), e considerar `_sumario_orgao` tratar "sem resultado E status != done-nesta-sessão" como estado desconhecido em vez de default `True`/`True`.

### P2 — `select_commands` do fluxo interativo pode produzir `RunRequest.commands = frozenset()` sem aviso

`interactive/flow.py:111-128`: `select_commands` devolve `frozenset(selected) if selected else frozenset()` — um checkbox onde o usuário pode desmarcar todas as etapas. `_run_guided_flow` (linhas 154-163) passa esse frozenset vazio direto para `RunRequest.commands` sem validação alguma antes do `confirm`. `execute_run` (`orchestration/run.py:302-309`) trata isso silenciosamente: cada etapa do plano cai no ramo `command not in request.commands` e vira `status="skipped"`, sem nenhum erro/mensagem "nada foi selecionado". O usuário confirma, a execução "roda" e termina com código de saída 3 (produção pulada) e um painel cheio de `◌ skipped`, sem indicação clara de que a causa foi "nenhuma etapa escolhida" vs. alguma falha de dependência.

`cli/run.py`, em contraste, nunca expõe essa possibilidade — `RunRequest.commands` fica sempre no default `_ALL_COMMANDS` (`orchestration/run.py:45-47,61`), já que `run_run` (`cli/run.py:32-58`) não tem flag para restringir comandos.

Sugestão: `select_commands` deveria recusar seleção vazia (revalidar antes do `confirm`, como já faz para o formato de competência) ou `execute_run`/`_run_guided_flow` deveria emitir um aviso explícito quando `request.commands` é vazio.

### P2 — `competencia` sem validação de formato no entry point CLI direto; `orchestration` nunca revalida

`interactive/flow.py:47-52` valida `competencia` com `_COMPETENCIA_RE = ^\d{4}-\d{2}$` antes de aceitar a resposta. O subcomando `run` da CLI direta (`cli/main.py:294`, `run_parser.add_argument("competencia", ...)`) e o subcomando `measure` (linha 206) **não têm validação de formato alguma** — é um `str` argparse puro, repassado sem checagem por `_dispatch_run` (`cli/main.py:576-597`) até `RunRequest.competencia` (`orchestration/run.py:53`).

`orchestration` nunca revalida esse campo em lugar nenhum do próprio módulo — `execute_run`/`_ensure_state`/`state_path` (`orchestration/state.py:58-59`) usam `competencia` diretamente para montar o nome do arquivo de estado: `runs_dir / f"{competencia}-{orgao}.json"`. Uma competência digitada via `pyauditor run` contendo `/` (ex. `../../tmp/x`) produz um `Path` que escapa de `runs_dir` sem qualquer erro — grava/lê o JSON de estado fora do diretório esperado. Impacto real é baixo (CLI single-user local, conforme o próprio docstring de `state.py:8-11` já aceita ausência de locking como corte de escopo), mas é uma fronteira onde só um dos dois entry points valida a forma do dado antes de repassá-lo para `orchestration`, que confia cegamente nos dois.

Sugestão: mover a validação de `competencia` (o mesmo regex `^\d{4}-\d{2}$` já usado em `interactive/flow.py`) para dentro de `orchestration.run.execute_run` (ou `RunRequest.__post_init__`), para que ambos os entry points herdem a mesma garantia em vez de duplicar/faltar a checagem cada um a seu modo.

### P2 — `RunRequest.orgao: str` sem tipo restrito — `orchestration` confia no formato vindo de cada lado

`orchestration/run.py:54` declara `orgao: str` (comentário `# "MinC" | "MTur" | "both"`, não um `Literal`/enum de fato). `cli/main.py` usa `Orgao: TypeAlias = Literal["MinC", "MTur", "both"]` e restringe via `argparse` `choices=(...)` (`_add_orgao_argument`, linhas 141-148); `interactive/flow.py` restringe via lista fixa de opções do `ask_choice` (linhas 87-94). Hoje os dois entry points sempre entregam um valor válido, mas `orchestration._plan`/`_dispatch`/`_capa_path_for` não impõem nada — um terceiro chamador (teste, script futuro, ou um bug de digitação num desses dois pontos) que monte `RunRequest(orgao="minc")` ou `orgao=""` passa batido: `_plan` (`orchestration/run.py:111-119`) trata qualquer valor diferente de `"both"` como se fosse um órgão único válido e monta caminhos (`data_dir / orgao`) silenciosamente errados, sem erro.

Sugestão: `orgao: Literal["MinC", "MTur", "both"]` no próprio `RunRequest`, ou validação explícita no início de `execute_run`.

### P2 — Fluxo interativo não expõe `final_month`; `RunRequest.final_month` fica sempre `False` nesse caminho

`cli/main.py:309-313` expõe `--final-month` no subcomando `run` (repassado por `_dispatch_run`, linha 594, até `RunRequest.final_month`). `interactive/flow.py::collect_answers` (linhas 74-108) nunca pergunta por isso, e `_run_guided_flow` (linhas 154-163) monta `RunRequest` sem passar `final_month`, ficando no default `False` (`orchestration/run.py:60`). Efeito de negócio real: o item 35 do TR (desligar o rollover de glosa no último mês de vigência) é inacessível para quem usa o modo guiado — não há como um usuário do fluxo interativo gerar um relatório de encerramento de contrato correto.

Sugestão: adicionar a pergunta equivalente (`confirm`) em `collect_answers`, ou pelo menos documentar a lacuna como decisão consciente.

### P3 — Lista de comandos duplicada entre `orchestration/run.py` e `interactive/flow.py`

`orchestration/run.py:45-48` define `_ALL_COMMANDS`/`_PHASE_ORDER` com os 5 nomes de comando. `interactive/flow.py:24` redefine independentemente `_ALL_COMMANDS: Final[tuple[str, ...]] = ("bootstrap", "split", "measure", "report", "consolidate")` — mesma lista, literal duplicado, sem importar de `orchestration`. Se uma fase nova for adicionada ao pipeline (`_PHASE_ORDER` em `orchestration/run.py`), a tela de seleção do fluxo guiado (`select_commands`, `interactive/flow.py:111-128`) não a descobre automaticamente — fica desatualizada em silêncio até alguém lembrar de editar os dois lugares.

Sugestão: `interactive/flow.py` importar a lista de comandos de `orchestration.run` em vez de redeclarar.

### P3 — `log_path` de `render_summary`/`show_summary` nunca é preenchido por nenhum dos dois entry points

`cli/run.py:60` chama `render_summary(run_result, output=output)` sem `log_path`, embora `cli/main.py::_dispatch_run` (linhas 581-583) já calcule um `_run_log_path(report_dir, _CMD_RUN, competencia)` só para `setup_logging` — nunca repassado adiante para o resumo. `interactive/flow.py:188` chama `provider.show_summary(run_result)`, também sem `log_path`; e o modo interativo (`interactive/__init__.py`) nunca chama `setup_logging` em lugar nenhum — não existe arquivo de log dedicado para essa via. Resultado: a linha "Log completo: ..." documentada em `orchestration/summary.py:392-393` nunca aparece em nenhum dos dois modos — parâmetro morto na prática nos dois lados da fronteira.

Sugestão: `_dispatch_run` repassar o `Path` de `_run_log_path` para `run_run`/`render_summary`; decidir se o modo interativo também deveria ter um log de arquivo (hoje não tem nenhum).

### Fricção CSV+YAML nesta fronteira

O único ponto onde esta fronteira toca leitura de config declarativa é `_manifest_for` (`orchestration/run.py:185-187`): `manifest_path = per_orgao_config_dir / "datasets.yaml"; return load_manifest(manifest_path) if manifest_path.exists() else None`. Essa mesma checagem "existe? senão `None`" está duplicada de forma independente em `cli/main.py::_dispatch_measure` (linhas 441-442) e `cli/main.py::_dispatch_split` (linhas 476-478) — três cópias da mesma regra "manifesto ausente = `None` silencioso, sem warning", uma em cada lugar que precisa montar o caminho de `datasets.yaml`. Não há um único ponto de verdade para essa convenção de caminho (`<config_dir>/<orgao>/datasets.yaml`); se a convenção mudar, os três precisam ser atualizados em lockstep, e nada impede que um seja esquecido — o tipo de fragilidade que o modelo YAML-sem-schema-compartilhado já mostrou aqui (nenhum crash hoje, mas nenhuma garantia de sincronia futura). Severidade P3 (nenhum bug ativo observado, mas duplicação real de uma regra de convenção de arquivo).

### Síntese

O achado mais grave (`_capa_path_for` divergente, P1) é um bug de comportamento real e silencioso: os dois entry points já produzem resultados diferentes em disco para o mesmo comando com os mesmos flags, dependendo de qual caminho de código foi usado (`cli/main.py` direto vs. `orchestration/run.py` via `run`/interativo). O segundo P1 (defaults otimistas no resumo do resume interativo) é uma perda silenciosa de sinal de corretude — o painel final pode alegar "liberado para publicação" sem ter recalculado nada nesta sessão. Os demais achados (P2/P3) são lacunas de validação/paridade de features entre os dois entry points que hoje não quebram nada visivelmente, mas dependem inteiramente de cada ponto de entrada se autodisciplinar, sem nenhuma garantia imposta por `orchestration`.
