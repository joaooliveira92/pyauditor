Type: prototype
Status: resolved
Blocked by: 02, 04

## Question

Desenhar o fluxo de telas do modo guiado, do começo ao fim, como um protótipo navegável (transcript ou mock de terminal) para reagir em cima — não é para chegar a código de produção.

Cobrir:

- Tela de abertura: mensagem explicando o objetivo da ferramenta, ações disponíveis, como pedir ajuda contextual em cada etapa.
- Coleta progressiva: prompts para `competencia` (validação `YYYY-MM`, mensagem de erro clara quando o formato está errado), `--orgao` (`MinC`/`MTur`/`both`, com o comportamento de `both` do ticket "Interactive layer architecture" refletido na UI), caminhos com defaults (config-dir/data-dir/output-dir/capa-path), e como voltar/revisar uma resposta já dada.
- Seleção de Commands a rodar: pipeline completo vs. subconjunto — como a lista de Commands é apresentada (usando `questionary` multi-select, per decisão de fundação), com as dependências entre eles (ticket "Dependency enforcement") visíveis e combinações inválidas bloqueadas na própria tela, não só num erro depois.
- Execução: como cada Command state (pending/running/done/skipped/cancelled/error) aparece visualmente — cores/símbolos, exibição de progresso/duração.
- Falha durante a execução: como a tela oferece retry/skip/abort (o comportamento exato de cada opção é do ticket "Failure-handling flow" — aqui só a forma da tela).
- Resumo final: como os campos do dataclass de resultado (ticket "Structured result dataclasses") — artefatos gerados, avisos, falhas — viram uma tela de resumo legível, mais "próximos passos" e o mapeamento para o código de saída.

Capturar o protótipo numa branch `prototype/interactive-cli-ux`, fora do master, e linkar como asset na resolução do ticket.

## Answer

Protótipo capturado em `.scratch/interactive-cli/prototype_guided_flow.py` na branch `prototype/interactive-cli-ux` (commit `4ba2df4`) — script Python executável com `rich`+`questionary` (as bibliotecas já travadas), rodável de verdade (`python .scratch/interactive-cli/prototype_guided_flow.py`), com dados forjados no lugar de Commands reais e uma falha embutida na 3ª etapa para exercitar a tela de erro.

Formato de cada tela, validado:

- **Abertura**: painel único com objetivo da ferramenta + instrução de que `?` em qualquer pergunta mostra ajuda contextual e Ctrl+C encerra sem perder o preenchido (ajuda contextual vira um padrão uniforme — loop de pergunta que intercepta `?` — em vez de um comando de help separado).
- **Coleta progressiva**: `competencia` validado inline (mensagem de erro clara no formato esperado), `--orgao` com `both` explicado via ajuda, caminhos com defaults mostrados entre colchetes, e uma tela de confirmação final que, se recusada, reentra na coleta (voltar/revisar) — numa implementação real cada campo viria pré-preenchido com a resposta anterior.
- **Seleção de Commands**: `questionary.checkbox` com `consolidate` **desabilitado** (não apenas avisado) quando `--orgao` não é `both` — a forma visual do `DependencyCheck` do ticket "Dependency enforcement": combinação inválida fica impossível de selecionar, não só um erro depois.
- **Execução**: tabela ao vivo (símbolo + cor por Command state — `○` pending, `◐` running, `●` done, `◌` skipped, `✕` cancelled/error — mais duração), redesenhada a cada transição de estado via `console.status`/spinner do `rich`.
- **Falha**: painel vermelho com o motivo específico (equivalente ao `error_message` do ticket "Structured result dataclasses") e um `questionary.select` com Tentar novamente/Ignorar/Abortar — só a forma; a semântica exata de cada opção fica para o ticket "Failure-handling flow" (marcado explicitamente no protótipo como não decidido aqui).
- **Resumo**: tabela final de estados + painel de artefatos gerados + caminho do log (`loguru`, escrito em paralelo, nunca um painel ao vivo — decisão do ticket "Interactive layer architecture") + painel de próximos passos + código de saída — conteúdo exato dos campos fica para o ticket "Completion summary and exit codes".

Nenhuma decisão nova travada além da forma das telas — os três tickets ainda abertos que este protótipo deliberadamente não resolveu (semântica de retry/skip/abort, conteúdo exato do resumo, texto final em português) seguem como próximos tickets do mapa.
