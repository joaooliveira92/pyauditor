# 03 - Contrato de códigos de saída

Type: grilling
Status: resolved

## Question

Qual o contrato de **códigos de saída** da CLI? Hoje `cli/results.py` e `orchestration/summary.py` reduzem tudo a `0` (done) ou `1` (erro), sem distinguir "concluído com pendência impeditiva" de "falha técnica" — o que esconde de CI/workers uma execução que produziu relatório, mas com dados incompletos ou cálculo indisponível.

Decisões em aberto:
- Convenção completa (0 = válido; 1 = falha técnica; 2 = uso inválido; 3 = dados obrigatórios incompletos; 4 = cálculo financeiro indisponível) ou versão reduzida (0/1/2)?
- Os códigos aplicam-se a `run` apenas, ou também a `measure`/`report`/`consolidate` individuais?
- Como o resumo final (ticket 04) exibe o status global coerente com o código de saída?
- `skipped` de um comando dependente deve alterar o código de saída? (hoje `exit_code_for_run` trata skipped como não-falha.)

Depende: ticket 02 (o que conta como "pendência impeditiva") e ticket 01 (cálculo financeiro indisponível = status distinto).

Contexto: review.md §"Comportamento sugerido para o código de saída" e §4 (execução sem status final inequívoco).

## Answer

Contrato fechado por grilling (HITL), na rodada completa (Q1–Q8, todas aprovadas):

1. **Tabela completa (5 códigos)** — não a versão reduzida:
   - `0` **CONCLUÍDO** — válido e publicável;
   - `1` **FALHA** — qualquer Command `error` (falha técnica / artefato não gerado);
   - `2` **USO INVÁLIDO** — parse/argumentos inválidos (argparse + `main.py:409`), exclusivo, nunca coexiste com resultado de run;
   - `3` **CONCLUÍDO COM PENDÊNCIAS** — balde único de "não-publicável": dados obrigatórios incompletos (rascunho) ou etapa de produção `skipped`;
   - `4` **CÁLCULO FINANCEIRO INDISPONÍVEL** — glosa não calculada (valor mensal ausente → `objetos.csv` não cobre; ticket 01).
2. **Escopo**: a tabela cheia vale para `run`/`report`/`consolidate`. `bootstrap`/`measure` não produzem artefato financeiro → permanecem `0`/`1`.
3. **Precedência global (agregado por órgão, pior vence)**: `1 > 4 > 3 > 0`.
4. **`skipped` de produção**: `report`/`consolidate` `skipped` → código **3** (resultado financeiro incompleto nunca vale `0`) — revisão da decisão interactive-cli "skipped jamais é falha", que continua valendo para `bootstrap`/`measure` e para o modo guiado (o humano ainda pode decidir skip).
5. **Warnings não-bloqueantes não afetam o código** — ficam no resumo/contagem (capa reutilizada, divergência informativa).
6. **`3` é balde único** (rascunho/dados incompletos/não publicável); a granularidade (quais campos, qual órgão) vive no resumo/JSON (ticket 04).
7. **Nomes estáveis** (em `cli/results.py::_EXIT_NAMES`) — o resumo final (ticket 04) exibe exatamente o mesmo rótulo do código de saída, para nunca divergirem.

**Implementação embarcada no mapa** (nota do esforço: ticket resolvido → mudança no código):
- `cli/results.py`: vocabulário `ExitCode`, `_EXIT_NAMES`, `exit_code_name`, `is_production_command`, e `exit_code_for_results` agora flag-agreggado (`1>4>3>0`); sinais via duck-attr `publicable`/`glosa_calculada` para não criar ciclo de import.
- `cli/report.py`: `ReportResult.publicable` (obrigatórios-para-publicar ausentes → rascunho, ticket 02) e `ReportResult.glosa_calculada` (valor mensal presente, ticket 01).
- `cli/consolidate.py` + `excel/consolidate.py`: `ConsolidateResult.glosa_calculada` / `ConsolidationResult.glosa_calculada` (valor_base presente), e log "glosa: não calculada".
- `orchestration/summary.py`: `exit_code_for_run(state_commands, results)` com a precedência (1/4/3/0); callers `cli/run.py` e `interactive/provider.py` atualizados.
- `cli/main.py`: dispatch de `consolidate` reduz pelo `exit_code_for_results` flag-aware.

Testes atualizados: `tests/test_orchestration_summary.py` (precedência 0/3/4/1 e skip de produção), `tests/test_cli_run.py` (capa em branco → `4`). Suíte 256 passed; mypy limpo nos arquivos tocados (erros pré-existentes em `tests/test_glosas.py` intocados).