Type: research
Status: resolved

## Question

`cli/main.py` faz o parsing de argparse e despacha para `_dispatch_measure`/`_dispatch_bootstrap`/`_dispatch_report`/`_dispatch_consolidate`/`_dispatch_run`/`run_split` (`cli/split.py`). Rastreie a fronteira entre o parsing (flags, formato de `competencia`, `orgao`) e cada comando: onde a validação é feita uma vez no parsing vs. duplicada/ausente em cada `_dispatch_*`/`run_*`; onde `main.py`'s pre-flight checks (`CHECKERS`/`dependency_missing`) batem ou não com o que cada comando realmente precisa; se `run_split` (novo, adicionado após o diagnóstico anterior) segue o mesmo padrão de validação/erro acionável dos demais comandos ou diverge.

Registre também fricção concreta do modelo CSV+YAML nesta fronteira, se houver.

Aplique o skill `python-production-engineer` (ler `.agents/skills/python-production-engineer/SKILL.md` por inteiro) para julgar severidade. Achados citam `file:line`.

## Answer

Investigação cobriu `src/pyauditor/cli/main.py` por inteiro (parsing, `_extract_*_request`, todos os `_dispatch_*`), `cli/dependencies.py`, e cada módulo despachado por inteiro: `bootstrap.py`, `measure.py`, `report.py`, `consolidate.py`, `split.py`, `results.py`, além de `orchestration/run.py` (o outro consumidor de `CHECKERS`/`dependency_missing`, necessário para julgar se o padrão de `main.py` é consistente com o do orquestrador de `run`).

### P2 — `competencia` não é validada antes de `main.py` já ter construído paths com ela (todos os comandos, `split` incluso)

`build_parser` (main.py:198-323) declara `competencia` como positional sem `type=` validador (ex.: `measure_parser.add_argument("competencia", ...)` em main.py:206; idem em report/consolidate/split/run: linhas 240, 266, 279, 294) — diferente de `--orgao`, que argparse já valida via `choices=(...)` em `_add_orgao_argument` (main.py:141-148). `validate_competencia()` (cli/results.py:29-36) só roda dentro de `run_measure`/`run_split`/`run_report`/`run_consolidate`, ou seja, depois que `main.py` já usou a string crua para montar diretórios:

- `_dispatch_measure` (main.py:423-431): `log_path=_run_log_path(request.output_dir / request.orgao / request.competencia, ...)`, chamado antes de `run_measure`.
- `_dispatch_split` (main.py:462-470): mesmo padrão com `request.data_dir`.
- `_extract_report_request` (main.py:390-404) já monta `output_path=output_dir / f"relatorio_{competencia}_{orgao}.xlsx"`, usado por `_dispatch_report` (main.py:505-511) antes de `run_report` validar.
- `_extract_consolidate_request` (main.py:407-416) monta `output_path=report_dir / f"relatorio_{competencia}_consolidado.xlsx"`, usado por `_dispatch_consolidate` (main.py:547-554) antes de `run_consolidate` validar.

`setup_logging` (logging.py:95-98) faz `path.parent.mkdir(parents=True, exist_ok=True)` incondicionalmente. Ou seja: uma `competencia` malformada (ex.: contendo `/` ou `..`) já cria diretórios/arquivo de log fora do padrão esperado *antes* do erro acionável de `validate_competencia` aparecer — o próprio docstring de `validate_competencia` (results.py:29-36) promete que "toda subcommand que transforma competencia em path... deve chamar isto antes de construir qualquer path", mas é `main.py`, não os `run_*`, quem constrói o primeiro path (log). `split` segue exatamente o mesmo padrão dos demais — não diverge aqui, mas também não escapa do problema.

Sugestão: validar `competencia` uma vez em `cli_main`/em cada `_dispatch_*`, logo após o parse e antes de qualquer `_run_log_path`/`_extract_*_request`, saindo com o código 2 (uso inválido) — mesmo tratamento que `--orgao` já recebe via `choices`.

### P2 — Log de `split` cai numa pasta que não corresponde aos artefatos que gerou

`_dispatch_split` (main.py:462-470) chama `_run_log_path(request.data_dir / request.orgao / request.competencia, _CMD_SPLIT, ...)`. Dois problemas concretos:

1. Com `--orgao both`, nesse ponto `request.orgao` ainda é a string `"both"` (o loop por órgão só acontece depois, main.py:472-486) — o log vai para `<data-dir>/both/<competencia>/`. Diferente de `measure`, cujo diretório `.../both/<competencia>/` é significativo porque `write_combined_roms` (main.py:455-458, measure.py:299-334) de fato escreve ROMs combinados ali, `split` não tem nenhum passo "both" equivalente — a pasta `both/` fica órfã, sem nenhum outro artefato.
2. Mesmo no caso de um único órgão, o diretório de log usa a convenção "competencia como um único segmento" (`<data-dir>/<orgao>/<competencia>/`), mas os artefatos reais de `split` vivem em `<data-dir>/<orgao>/<YYYY>/<MM>/_split/...` (split.py:159-162, `competencia_data_dir = data_dir / year / month`). Essa convenção de path único por competência é a do lado de *saída* (ROMs, `roms/<orgao>/<competencia>/...`), não a do lado de *entrada* onde `split` escreve (`input/<orgao>/<YYYY>/<MM>/...`). O log de `split` acaba numa pasta paralela e desconectada da árvore `_split/` que ele realmente populou.

Sugestão: espelhar a convenção que o próprio `run_split` usa para `competencia_data_dir` (`data_dir/orgao/year/month`) ao montar o log path, e evitar a pseudo-pasta `both/` quando não há passo combinado — por exemplo, logar por órgão dentro do loop (como `bootstrap` já faz, ver achado abaixo) em vez de uma vez só antes dele.

### P2/P3 — `CHECKERS`/pre-flight não é usado por `cli/main.py`; só por `orchestration/run.py`

`cli/dependencies.py:20-26` registra checkers para `bootstrap`, `split`, `measure`, `report`, `consolidate`, mas `main.py` nunca importa `CHECKERS` nem os checkers individuais de bootstrap/split/measure. `_dispatch_report` (main.py:519-533) e `_dispatch_consolidate` (main.py:555-565) chamam explicitamente `check_report_ready`/`check_consolidate_ready` antes de rodar o comando — só esses dois têm pre-flight em `main.py`. `_dispatch_measure`, `_dispatch_split` e `_dispatch_bootstrap` (main.py:423-502) nunca chamam `check_measure_ready`/`check_split_ready`/`check_bootstrap_ready`.

Hoje isso não muda comportamento nenhum porque as três funções são stubs que sempre retornam `satisfied=True` (bootstrap.py:33-35, measure.py:76-79, split.py:80-83, todas com a mesma assinatura `(*_args, **_kwargs)`). Mas é uma armadilha de manutenção: o único lugar que de fato invoca esses três checkers via o registro é `orchestration/run.py` (`dependency_missing`, run.py:163-182, `CHECKERS[command]()` na linha 181) — usado apenas pelo comando composto `pyauditor run`. Se algum dia `check_split_ready` ganhar lógica real (ex.: validar `categorias.yaml` antes de rodar `split` isolado), essa checagem só vai disparar quando o usuário roda `pyauditor run`; chamar `pyauditor split`/`pyauditor measure`/`pyauditor bootstrap` direto pula o pre-flight silenciosamente, porque `main.py` nunca consulta o registro nem os checkers individuais dessas três.

Sugestão: ou (a) aplicar em `main.py` o mesmo padrão explícito que `report`/`consolidate` já têm — chamar o checker de cada comando em seu `_dispatch_*` antes de rodar —, ou (b) documentar no próprio `CHECKERS`/nos três checkers stub que hoje eles só são exercitados via `pyauditor run`, para que uma futura implementação real não assuma cobertura que não existe.

### P3 — Fricção CSV+YAML: `--manifest` default duplicado e carregamento silencioso quando `datasets.yaml` falta

`_extract_measure_request` (main.py:330-335) e `_extract_split_request` (main.py:350-355) recomputam de forma independente o mesmo default (`config_dir / orgao / "datasets.yaml"`) — duplicação, não é fronteira crítica por si só, mas é sintoma do próximo ponto: `_dispatch_measure` (main.py:440-442) e `_dispatch_split` (main.py:476-478) fazem, cada um separadamente:

```python
if per_orgao_manifest_path.exists():
    manifest = load_manifest(per_orgao_manifest_path)
```

Se `datasets.yaml` não existir, `manifest` fica `None` silenciosamente — nenhum log (nem DEBUG) registra que o manifesto esperado não foi encontrado. É exatamente o "default silencioso quando falta uma config YAML" que o mapa pede para registrar como fricção: o operador só percebe a ausência do manifest se algo mais adiante (`resolve_source`) falhar por outro motivo, e mesmo aí a mensagem não aponta de volta para "o `datasets.yaml` esperado nunca foi carregado".

Sugestão: emitir ao menos um evento DEBUG/INFO quando o manifest esperado não existe (mesmo que a ausência seja um fallback válido para a convenção de nomes), e extrair a lógica "resolve manifest path + carrega se existir" — hoje duplicada linha a linha entre `_dispatch_measure` e `_dispatch_split` — para uma função compartilhada em `main.py`.

### P3 — `bootstrap` divide o log em um arquivo por órgão; os demais comandos usam um único log para `--orgao both`

`_dispatch_bootstrap` (main.py:490-502) chama `setup_logging(...)` *dentro* do loop `for single_orgao in _each_single_orgao(orgao)`, uma vez por órgão — cada chamada cria um novo arquivo de log com timestamp próprio (`_run_log_path` usa `datetime.now()` a cada chamada, main.py:382-387) e, por design, `setup_logging` remove os handlers anteriores (logging.py:87). Já `_dispatch_measure`, `_dispatch_split`, `_dispatch_report` e `_dispatch_consolidate` chamam `setup_logging` uma única vez, antes do loop por órgão, produzindo um único arquivo de log cobrindo os dois órgãos quando `--orgao both`. Resultado: com `pyauditor bootstrap --orgao both`, o usuário recebe dois arquivos de log separados (um por órgão) em vez de um único log da execução, diferente de todo o resto do CLI. Não é um bug de perda de dado (nada é sobrescrito), mas é uma inconsistência de observabilidade sem justificativa documentada.

Sugestão: mover a chamada de `setup_logging` para fora do loop em `_dispatch_bootstrap`, igual aos outros quatro dispatchers, ou documentar explicitamente por que `bootstrap` quebra o padrão.

### Síntese: `split` diverge dos demais?

Na validação de `competencia`/pre-flight, `split` segue exatamente o mesmo padrão (correto ou não) que `measure`/`bootstrap`: validação tardia dentro de `run_split`, sem checker real em `check_split_ready`, sem pre-flight explícito em `main.py`. Não há divergência de `split` em relação a essa família de comandos. A divergência real e nova que `split` introduz é o path do log (achado P2 acima): ao herdar a convenção de "competencia como diretório único" de `measure`/`report` (lado de saída) só que aplicada ao `data_dir` (lado de entrada, que usa convenção `<ano>/<mês>`), o log de `split` fica desconectado dos artefatos reais que gera — um problema que nenhum outro comando tem, porque nenhum outro grava múltiplos artefatos por competência diretamente sob `data_dir`.

