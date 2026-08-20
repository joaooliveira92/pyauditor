# 05 - Logs dos indicadores e observabilidade

Type: grilling
Status: resolved
Blocked by: 04

## Question

Como devem ser os **logs dos indicadores** e a política de verbosidade? Hoje cada indicador loga apenas `INMS 1.1: roms\MinC\2026-06\INMS-01.md` — não fica claro se o arquivo foi localizado, validado, processado ou é só entrada; e não há contexto estável (órgão, competência, status, duração).

Decisões em aberto:
- Vocabulário dos eventos: `event=indicator_measured`, `orgao`, `competencia`, `indicator`, `rom_path`, `status`, `duration_ms` — registrar só o mínimo operacional necessário (evitar dados sensíveis).
- Formato por verbo: `indicador apurado: código=INMS-1.1 rom=...` + resultado essencial (`pontos=... status=conforme`).
- Política de verbosidade: padrão = etapas/pendências/resumo; `-v` = um evento por indicador; `-vv` = detalhes de leitura/validação/cálculo; `--log-format json` = todos os eventos estruturados.
- Onde entra o JSON: substituir o formato visual amigável ou coexister (CLI amigável por padrão, JSON opcional)?

Depende parcialmente de ticket 04 (resumo conciso `MinC: 14/14` é o padrão que o `-v` detalha).

Contexto: review.md §5 e §"Prioridade 3: melhorar observabilidade" e §"Prioridade 4: reduzir ruido".

## Answer

Fechado por grilling (Q1-Q9, todas aprovadas). Política de verbosidade e vocabulário de eventos decididos:

1. **Evento por indicador (Q1/Q7)**: verbo + contexto estáble — `indicador apurado | orgao=MinC codigo=INMS-1.1 rom_path=... status=conforme` — no lugar de `INMS 1.1: roms\...`. O `rom_path` relativo (portabilidade no 06).
2. **Política de verbosidade (Q2/Q8/Q9)**: padrão (INFO) = etapas/pendências/resumo, **sem linha por indicador** (antes eram 28 linhas); `-v` (DEBUG) = um evento por indicador; `-vv` = detalhes; `--log-level` explícito prevalece sobre `-v`; `--log-format json` estrutura o stderr. Flags em **todos** os subcomandos.
3. **Interface com 03/04 (Q3)**: `--log-format json` (logs, stderr/arquivo) é **separado** de `--output json` (resumo 04, stdout) — cada um controla sua superfície; coexistem.
4. **JSON (Q4)**: `serialize=True` do loguru — uma linha JSON por registro com `record.extra` (evento + contexto). Filtro: o contexto que se passa a `log_event` é só operacional (o código não passa conteúdo de dados sensibles) — a tração está ao nível de quem emite.
5. **Níveis (Q5/Q6)**: INFO = etapas/resumo; DEBUG = por indicador; WARNING = pendências; ERROR = falhas. O painel "Resultado" (04) **no muda** — o conciso `MinC: 14/14` é log, não painel.

**Implementado no código**:
- `logging.py`: `log_event(event, verb, level, **context)` (texto chave=valor + `event` reservado p/ JSON); `resolve_log_level`; `setup_logging(..., verbose, log_level_explicit, json_format)` com `serialize=True`.
- `cli/measure.py`: por indicador `log_event(indicator_measured, ...)` **DEBUG** (só `-v`); resumo conciso por órgão `INFO measure_done: MinC: N/N indicador(es) apurado(s)`; reusa `summarize(result)`.
- `cli/bootstrap.py`: eventos `capa_created`/`capa_reused` ("capa existente será reutilizada" — corrige achado §3).
- `cli/report.py`: `glosa_nao_calculada` (WARNING, motivo=valor mensal ausente) e `report_generated` (status rascunho/publicavel).
- `cli/consolidate.py`: `decisoes_preservadas` e `consolidate_generated` (glosa no calculada/total_pontos).
- `cli/main.py`: `-v`/`-vv`, `--log-level`, `--log-format {text,json}` em todos os subcomandos; `_logging_kwargs` (TypedDict) passa a `setup_logging`.

Testes: `tests/test_logging.py` (resolve_log_level, log_event texto/None omitido, `--log-format json` estrutra `record.extra`). Suíte 262 passed; mypy limpo; ruff sem violações novas (baseline de main.py mantido).

Desbloquea o ticket 06. A névoa "Validação de indicadores" (nº esperado = 14) **no se decide aquí** — segue em Not yet specified.