Type: grilling
Status: resolved
Blocked by: 01, 02, 05

## Question

Decidir a semântica exata de retry/skip/abort quando um Command falha durante um Run guiado, agora que o dataclass de resultado (ticket "Structured result dataclasses"), a validação de dependências (ticket "Dependency enforcement") e a forma das telas (ticket "Guided flow UX screens") estão resolvidos.

Decidir:

- Quais categorias de falha existem hoje (erro de validação de entrada, `OSError` de I/O, `hard_failure` de medição — nenhuma linha sobreviveu aos quality gates, exceção inesperada) e qual delas permite retry, qual permite skip, qual força abort — nem toda falha é igualmente segura de pular (ex.: pular `measure` com hard failure deixa `report` sem ROMs — colide com a validação de dependências do ticket 02).
- "Retry": re-executa o mesmo Command do zero com o mesmo Request, ou permite editar a entrada antes de tentar de novo (ex.: corrigir um `--data-dir` errado)? Isso reusa o "voltar/revisar" do ticket de telas de UX, ou é um caminho separado?
- "Skip": marca o Command como `skipped` no run-state (ticket "Run orchestrator and resume") e segue para o próximo — mas se o próximo depende do que foi pulado, a validação de dependências bloqueia automaticamente, ou o usuário já foi avisado na hora do skip?
- "Abort": encerra o Run preservando o run-state como está (para resumir depois) — nunca apaga contexto já preenchido, por requisito explícito do pedido original.
- Como cada mensagem de erro vira acionável (não só "falhou", mas "o que fazer") — existe um catálogo de mensagens por categoria de falha, ou isso fica a critério de cada Command?

## Answer

- **Duas situações de falha, duas telas**: (a) checagem de dependência falha **antes** do despacho (Command nunca rodou — ex.: retomando um Run onde um arquivo foi apagado externamente entre sessões) — tela oferece só "Ignorar esta etapa"/"Abortar a execução", sem "Tentar novamente" (nada mudou no mundo entre a checagem e uma nova tentativa, então repetir é determinístico e inútil). (b) o Command rodou e `Result.status` veio `"error"` — tela oferece as três opções, porque uma execução real pode plausivelmente ter sucesso numa nova tentativa (I/O transiente, espaço em disco liberado, permissão corrigida).
- **Semântica de "Tentar novamente"**: re-executa o mesmo `Request` do zero, sem edição inline. Se o usuário precisa de argumentos diferentes, aborta (preservando o run-state) e reinvoca com novas flags — não cresce um quarto caminho de "editar e tentar de novo" na tela, mantém as três opções já validadas no protótipo. Retry de `measure` roda **todos** os indicadores de novo, não só o que falhou (granularidade por-Command, já travada) — seguro, porque `run_measure` já sobrescreve os arquivos de ROM incondicionalmente a cada chamada.
- **Cascata de skip**: ao pular um Command, o orquestrador marca proativamente todo Command do plano atual que depende transitivamente dele como `skipped` também, com uma única mensagem consolidada ("measure, report e consolidate ficarão pulados") — em vez de forçar o usuário a passar por uma tela de falha separada para cada Command a jusante cujo destino já era conhecido no momento do skip.
- **Estados de Command além de `done`, refinando o ticket "Run orchestrator and resume"**: usa só `skipped` tanto para a escolha direta do usuário quanto para a cascata acima — **sem** um estado `cancelled` separado (a distinção entre "você escolheu pular isto" e "isto foi pulado porque algo a montante foi pulado" não muda nenhum comportamento, então um segundo valor de enum seria uma distinção sem diferença). Retomada (próxima invocação) pula Commands cujo estado é `done` **ou** `skipped`; qualquer outro (`pending`, `error`) é re-tentado se selecionado de novo — um Command que ficou `error` é re-tentado automaticamente na próxima invocação, já que não está `done`; um que ficou `skipped` continua pulado a menos que o usuário o reselecione explicitamente na tela de seleção de Commands.
- **Sem catálogo de mensagens**: a tela de falha renderiza o que já existe — `Result.error_message` (ticket "Structured result dataclasses", já escrito por call site, ex.: "capa não encontrada — rode `pyauditor bootstrap` primeiro") literalmente, para falhas de execução; e `DependencyCheck.missing` (ticket "Dependency enforcement") como marcadores, para falhas de pré-despacho. Um catálogo separado seria uma segunda fonte de verdade paralela para manter sincronizada com call sites que já dizem a coisa certa.
