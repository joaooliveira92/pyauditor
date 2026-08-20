Type: grilling
Status: resolved
Blocked by: 01, 06

## Question

Decidir o conteúdo exato do resumo de conclusão e o mapeamento para código de saída, agora que o dataclass de resultado (ticket "Structured result dataclasses") e a semântica de retry/skip/abort (ticket "Failure-handling flow") estão resolvidos.

Decidir:

- Conteúdo do resumo: quais campos de cada Command result aparecem (artefatos gerados — caminhos de ROM/relatório/capa —, avisos, falhas, Commands pulados/cancelados) e como se agregam quando `--orgao both` rodou dois conjuntos de Commands.
- "Próximos passos": é uma lista estática por combinação de Commands rodados (ex.: "rode `pyauditor report` a seguir"), derivada da validação de dependências (ticket "Dependency enforcement"), ou outra coisa?
- Código de saída do Run inteiro: `0` só se todos os Commands terminaram `done`? Um Command `skipped` intencionalmente conta como sucesso para fins de código de saída? Isso precisa ser distinto do código de saída de cada `run_*` individual (ticket 01) — como se compõem.
- O resumo final é só apresentado na tela (modo interativo) ou também precisa existir em forma não-interativa para `pyauditor run` (ticket "Run orchestrator and resume") — mesmo conteúdo, sem os widgets do `questionary`/`rich` de tela cheia?

## Answer

- **Conteúdo e agregação com `--orgao both`**: um novo agregado `RunResult` (em `orchestration/`, ao lado de `execute_run`) reúne os `Result`s por Command que de fato rodaram, mais as entradas do run-state para Commands `skipped` (que nunca produziram um `Result`). Renderizado agrupado por órgão quando `--orgao both` rodou (espelhando a ordem fase-major — bootstrap/measure/report de MinC juntos, depois os de MTur, depois um único `consolidate`), cada Command mostrando ícone de estado, seus próprios campos de artefato (`output_path`/`capa_path`/etc. — não as 14 linhas de `IndicatorOutcome` de `measure`, só uma contagem mais as que tiveram `hard_failure=True`), `warnings`, e `error_message` quando falhou. Commands pulados mostram o motivo (cascata de qual falha a montante, per ticket "Failure-handling flow").
- **"Próximos passos" — computado, não estático**: reusa as mesmas funções checadoras do ticket "Dependency enforcement" contra os Commands ainda não `done` — pergunta ao checker de cada um "está satisfeito?" e lista os motivos de `missing` como próximos passos. Uma tabela estática seria um segundo lugar codificando "o que depende do quê", exatamente a duplicação que aquele ticket já descartou.
- **Código de saída — confirmado e finalizado**: `1` se algum Command do run-state está `error`, senão `0`. Um Command `skipped` (escolhido pelo usuário ou em cascata) **não** conta como falha — foi uma escolha deliberada e informada (ticket "Failure-handling flow"), não um resultado inesperado. Computado diretamente dos estados do run-state, não por OR dos `exit_code_for(status)` de cada `Result` individual (um Command `skipped` nunca produziu um `Result` para derivar um exit code). Isso só torna explícita a regra "skipped não é falha" que já estava implícita em "Run orchestrator and resume".
- **Uma única função de renderização, não duas implementações**: renderização de resumo é saída pura (sem prompting), então não precisa do `InteractionProvider` Protocol — a indireção do Protocol existe só para abstrair a parte que genuinamente difere entre TTY real e teste roteirizado (perguntar coisas). Uma função compartilhada `orchestration/summary.py::render_summary(run_result) -> None`, usando `rich.Console` diretamente, chamada identicamente por `cli/run.py` (modo não-interativo) e por `interactive/provider.py`'s `show_summary` (que só delega a ela). `cli/run.py` não precisa depender de `interactive/` para ter o mesmo resumo formatado; a saída determinística pode ser testada capturando o `rich.Console` direto, sem precisar do dublê de teste do Protocol.

Nenhum ticket novo surge desta resolução — é a última pergunta aberta no mapa.
