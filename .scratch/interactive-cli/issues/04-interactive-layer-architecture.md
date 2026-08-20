Type: grilling
Status: resolved
Blocked by: 01, 03

## Question

Decisão de fundação (map.md) já travou: nova package irmã (`src/pyauditor/interactive/`, nome a confirmar), dependência de mão única em relação a `cli/`/orquestração; `rich.Progress`/spinners para feedback (sem asyncio/threading); `questionary` para prompts multi-select; um protocolo injetável de prompt/output desde o início, para testabilidade sem TTY real.

Decidir, agora que o dataclass de resultado (ticket "Structured result dataclasses") e o orquestrador `pyauditor run` + run-state (ticket "Run orchestrator and resume") estão resolvidos:

- Estrutura interna da package: módulos por responsabilidade (ex.: `interactive/prompts.py`, `interactive/session.py`, `interactive/render.py`)? Nome final da package.
- Desenho exato do protocolo injetável — quais métodos abstrai (`ask_text`, `ask_choice`, `ask_confirm`, `show_progress`, `show_summary`...)? Uma única interface `InteractionProvider`, ou várias menores compostas?
- Como o protocolo real (produção) usa `questionary`+`rich` por trás, e como o protocolo de teste injeta respostas roteirizadas — que forma toma esse duplo em testes (fixture reutilizável em `tests/`)?
- Como a camada interativa consome o run-state (ticket 03) e a validação de dependências (ticket 02) — chama a mesma orquestração que `pyauditor run` usa, ou tem seu próprio laço fino por cima dela? (deve ser a mesma, por causa da restrição de não duplicar lógica de negócio — confirmar a costura exata.)
- Detecção de ambiente não-TTY (stdin via pipe/CI): a camada interativa detecta e recusa/avisa, ou isso é responsabilidade do ponto de entrada (`pyauditor` sem args) antes mesmo de instanciar a camada interativa? (fog do map.md — resolver aqui se a resposta ficar clara.)
- Como os logs `loguru` por-run existentes convivem com a UI interativa — arquivo de log continua sendo escrito em paralelo (silenciosamente) enquanto a tela mostra o resumo estruturado, ou existe algum painel de log ao vivo? (fog do map.md — resolver aqui se a resposta ficar clara.)

## Answer

- **Onde vive o orquestrador**: nova package irmã `src/pyauditor/orchestration/` (ao lado de `cli/` e `interactive/`), com o executor de Run — ex. `orchestration/run.py`, função `execute_run(request, on_state_change=...) -> RunResult` (ou uma classe pequena `Run`). O ticket "Run orchestrator and resume" desenhou o laço fase-major, a escrita do run-state e a checagem de dependência antes de cada despacho, mas não deu um lar a isso — este ticket resolve: não é lógica de parsing de CLI (isso é `cli/`), nem apresentação (isso é `interactive/`); é sequenciamento de pipeline que os dois modos precisam identicamente. `cli/run.py` (handler argparse de `pyauditor run`) vira um wrapper fino que chama `execute_run` com um `on_state_change` no-op; a camada interativa chama a **mesma função**, passando seu `InteractionProvider` como callback de mudança de estado. É a costura que garante zero lógica de negócio duplicada.
- **Estrutura e nome da package**: `src/pyauditor/interactive/`, dois módulos:
  - `interactive/provider.py` — o Protocol `InteractionProvider` + implementação de produção (`RichQuestionaryProvider`) envolvendo `rich`+`questionary`.
  - `interactive/flow.py` — a sequência de telas do fluxo guiado (abertura → coleta progressiva → seleção de Commands → laço de execução → resumo), chamando `orchestration.execute_run()` e renderizando só através do provider injetado.
  - `interactive/__init__.py` — expõe o ponto de entrada único `run_interactive()`, chamado por `cli_main` quando invocado sem argumentos.
- **Forma do protocolo**: um único `InteractionProvider` Protocol (não várias interfaces compostas) — `ask_text`, `ask_choice`, `ask_multi_choice` (seleção de Commands via `questionary`), `confirm`, `show_message(text, style)`, `show_progress(label)` (context manager envolvendo spinner/`Progress` do `rich`), `show_summary(run_result)`. Um único fluxo linear chama esses métodos em sequência — dividir em várias interfaces não compraria nenhuma costura real, já que toda implementação (real ou dublê) precisa de todos juntos de qualquer forma.
- **Dublê de teste**: `tests/support/fake_interaction_provider.py` — infraestrutura só de teste, fora de `src/`, reproduz uma lista roteirizada de respostas e grava toda chamada `show_*` para asserções, reutilizável como fixture.
- **Detecção de não-TTY**: responsabilidade do ponto de entrada (`cli_main`/`__main__`), **antes** de sequer importar/instanciar `interactive/` — mesmo padrão do princípio de pre-flight-no-despacho do ticket "Dependency enforcement". Se `stdin` não é um TTY, imprime mensagem clara ("nenhum terminal detectado — use um subcomando diretamente, ex.: `pyauditor measure 2026-06`") e sai com código não-zero, em vez de tentar lançar prompts `questionary` contra um pipe. `interactive/` fica livre da responsabilidade de detectar ambiente — pode assumir que sempre roda de fato interativamente.
- **Logs vs. UI ao vivo**: o arquivo de log `loguru` por-run continua sendo escrito silenciosamente em paralelo enquanto a tela mostra `rich.Progress` + o resumo estruturado — sem painel de log ao vivo. Um sink customizado de `loguru` plugado em `rich.Live` seria complexidade real para um requisito que ninguém pediu; o resumo estruturado (`Result`, ticket "Structured result dataclasses") já é mais útil que linhas de log cru para a tela final, e o caminho do arquivo de log pode simplesmente ser citado nesse resumo para quem quiser o detalhe.
