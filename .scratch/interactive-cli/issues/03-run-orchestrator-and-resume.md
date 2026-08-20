Type: grilling
Status: resolved
Blocked by: 01, 02

## Question

Decisão de fundação (map.md) já travou dois pontos: (a) um novo comando não-interativo `pyauditor run <competencia>` (nome exato a confirmar) encadeia bootstrap→measure→report→consolidate numa invocação scriptável; (b) resumibilidade via arquivo de estado JSON por run (ex.: `.pyauditor/runs/<competencia>-<orgao>.json`), granularidade por Command.

Decidir, agora que o dataclass de resultado (ticket "Structured result dataclasses") e a validação de dependências (ticket "Dependency enforcement") estão resolvidos:

- Contrato de argumentos exato de `pyauditor run`: recebe os mesmos flags que hoje se espalham por `measure`/`report`/`consolidate` (`--orgao`, `--config-dir`, `--data-dir`, `--output-dir`, `--capa-path`, `--final-month`)? Como resolve conflitos entre eles (ex.: `--capa-path` só faz sentido para bootstrap/report)?
- `--orgao both`: `run` roda a cadeia inteira para MinC, depois para MTur, depois `consolidate`? Ou intercala? (hoje `_each_single_orgao` em `cli_main` faz measure/report por órgão sequencialmente antes de seguir — confirmar se `run` segue o mesmo padrão.)
- Schema exato do arquivo de run-state: quais campos por Command (state, timestamps, resultado do ticket 01, mensagem de erro se houver)? Nome do arquivo — chave é só `(competencia, orgao)` ou precisa também identificar múltiplas tentativas do mesmo `(competencia, orgao)` (re-runs)?
- Ciclo de vida do arquivo: quando é criado, quando é atualizado (a cada Command? só no fim?), é apagado depois de um Run bem-sucedido ou fica como histórico? Race condition se dois processos miram o mesmo `(competencia, orgao)` ao mesmo tempo — trava de arquivo, ou não é um caso a se preocupar?
- Retomar (`--resume` ou detecção automática ao rodar `pyauditor run` de novo com o mesmo `(competencia, orgao)`?): pula Commands já `done`, mas o que acontece com um Command que ficou `running` quando o processo morreu (estado inconsistente) — vira `error`? é re-tentado do zero?
- Código de saída de `pyauditor run` quando algum Command falha no meio da cadeia: aborta os seguintes por padrão (respeitando a validação de dependências do ticket 02), ou existe modo `--continue-on-error` para pular e seguir?

## Answer

- **Nome e contrato de argumentos**: `pyauditor run <competencia>`, aceitando os mesmos flags já usados hoje — `--orgao {MinC,MTur,both}` (default `MinC`), `--config-dir`, `--data-dir`, `--output-dir`, `--capa-path`, `--final-month` — cada um aplicado a qualquer Command da cadeia que já o usa hoje (ex.: `--final-month` só afeta a chamada de `report`; `bootstrap` simplesmente o ignora). Sem lógica nova de resolução de conflito — reaproveita `_capa_path_for()` e a derivação de paths de output já existentes em `cli_main`, chamados uma vez por Command na sequência em vez de uma vez por invocação isolada.
- **Ordem com `--orgao both`**: "fase-major" — roda `bootstrap` para MinC e depois MTur, **depois** `measure` para MinC e depois MTur, **depois** `report` para MinC e depois MTur, **depois** um único `consolidate` (agnóstico de órgão). Reaproveita o fan-out por-comando já existente (`_each_single_orgao`) sem inventar um intercalamento novo. Também garante que, quando a fase de `report` começa, os dois órgãos já têm `bootstrap`+`measure` feitos — a checagem de dependência (ticket "Dependency enforcement") passa sem caso especial.
- **Schema do run-state**: um arquivo por `(competencia, orgao-selector)` — `orgao-selector` é o valor de `--orgao` da invocação (`MinC`/`MTur`/`both`), reutilizado/sobrescrito entre tentativas (nunca um arquivo novo por tentativa, diferente dos logs `loguru`):

```json
// .pyauditor/runs/<competencia>-<orgao-selector>.json
{
  "competencia": "2026-06",
  "orgao_selector": "both",
  "commands": [
    {"command": "bootstrap", "orgao": "MinC", "status": "done", "started_at": "...", "finished_at": "...", "error_message": null},
    {"command": "measure",   "orgao": "MinC", "status": "done", "started_at": "...", "finished_at": "...", "error_message": null},
    {"command": "consolidate", "orgao": null, "status": "pending", "started_at": null, "finished_at": null, "error_message": null}
  ]
}
```

`status` aqui é o Command state completo (`pending`/`running`/`done`/`skipped`/`cancelled`/`error`) — rastreamento do orquestrador, distinto do `Status` mais estreito nos dataclasses `Result` (que só conhece `done`/`error`, por chamada já concluída). O arquivo não guarda o `Result` completo (paths, `IndicatorOutcome` por indicador) — só o necessário para decidir pular ou não, evitando reconstruir/duplicar o que já foi decidido no ticket 02 (filesystem é a fonte de verdade para dependências, não o run-state).

- **Ciclo de vida**: criado sob demanda no primeiro Command despachado (não pré-criado vazio no início do Run), atualizado após cada Command terminar (nunca no meio de um Command). Nunca apagado automaticamente após sucesso — uma invocação repetida contra um arquivo totalmente `done` simplesmente pula tudo e sai com `0`, regra mais simples que "apagar no sucesso" e consistente com os logs `loguru` por-run, que também nunca são limpos.
- **Concorrência**: sem trava de arquivo para dois processos mirando o mesmo `(competencia, orgao-selector)` simultaneamente — limitação aceita e documentada, não construída preventivamente (fiscalização é fluxo de um usuário só, não altamente concorrente).
- **Retomada**: sem flag `--resume` — rodar `pyauditor run <competencia> --orgao X` de novo encontra automaticamente o arquivo de estado em `.pyauditor/runs/<competencia>-<orgao-selector>.json` e pula qualquer Command já `done`. Um Command que ficou `running` quando o processo morreu é tratado como obsoleto na próxima invocação — resetado para `pending` e re-executado do zero (nunca retomado no meio, consistente com a granularidade por-Command já travada no mapa).
- **Falha e código de saída**: quando um Command falha no meio da cadeia, os seguintes são abortados por padrão — o que já acontece de graça, porque a checagem de dependência do próximo Command (ticket "Dependency enforcement") vai reportar `satisfied=False` já que a saída do Command que falhou não existe. Sem `--continue-on-error` — mesmo raciocínio do ticket "Dependency enforcement" que descartou `--force` (flag especulativa sem necessidade concreta). Código de saída geral do Run: `1` se algum Command terminou `error`, senão `0`.

**Emenda (ticket "Failure-handling flow")**: a regra de retomada acima ("pula qualquer Command já `done`") ficou mais precisa — pula Commands `done` **ou** `skipped`; qualquer outro estado (`pending`, `error`) é re-tentado se selecionado de novo. Também: o vocabulário de Command state usado no run-state não precisa de um valor `cancelled` separado — cascata de skip usa `skipped` também. Ver a resposta completa em [Failure-handling flow](06-failure-handling-flow.md).
