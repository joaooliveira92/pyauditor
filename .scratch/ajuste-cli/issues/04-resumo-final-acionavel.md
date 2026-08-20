# 04 - Resumo final acionável

Type: prototype
Status: resolved

## Question

Qual a forma do **resumo final** de uma execução — o estado global inequívoco que permite a uma pessoa (ou automação) decidir imediatamente se há ação pendente?

Hoje `orchestration/summary.py` imprime uma tabela de comandos com estados, mas sem status global, contagens de warnings/erros, status da glosa, duração, caminhos completos (a linha do consolidado truncada via rich) ou indicação de publicação bloqueada/liberada.

Decisões em aberto:
- Layout do resumo final (tabela atual + painel de resultado? blocos por órgão?).
- Quais linhas são indispensáveis: status global, competência, órgãos processados, indicadores, relatórios, consolidado, avisos/erros, glosa (calculada ou não), publicação (bloqueada/liberada), duração, caminhos completos.
- Verbo/evento por indicador no lugar de `INMS 1.1: roms\...` — e o resumo conciso `MinC: 14/14 indicadores apurados`.
- Onde os caminhos completos aparecem (após a tabela, sem truncamento).
- Saída estruturada para automação (`--output json`)? — interface com ticket 03 e 06.

Tipo prototype: gerar um protótipo do resumo (rich e/ou JSON) para reagir, antes de decidir o contrato final.

Depende: ticket 01 (status da glosa) e ticket 02 (publicabilidade). Alimenta ticket 06 (truncamento/portabilidade).

Contexto: review.md §4 e §"Exemplo de output mais claro".

## Answer

Fechado por grilling (Q1–Q10, todas aprovadas) com **protótipo rico+JSON** (ticket de tipo prototype) para reação. O protótipo foi capturado como fonte primária na branch **`prototype/resumo-final`** (commit `dc63f6b`, `.scratch/ajuste-cli/prototype_resumo_final.py`) — fora da main, como o skill prototype manda.

Decisões:
1. **Saída estruturada**: `--output json` no `run` coexiste com o painel rico (`text` é o padrão). Máquina recebe JSON (ponto decimal, caminhos completos); humano recebe o rich. É o mesmo estado global do código de saída — CI nunca parseia texto.
2. **Layout**: tabela única de etapas (a atual) **+ painel "Resultado"** (não blocos por órgão na tabela; o per-órgão vive no JSON).
3. **Painel (Q3/Q9/Q10)**: Resultado (nome do código, ticket 03), Competência, Órgãos processados, Indicadores apurados (`N/N`), Relatórios individuais (`N (K rascunho — <órgão>)` quando houver), Relatório consolidado (gerado/não gerado), **Avisos/Erros reais** (soma de `warnings` dos resultados / nº de Commands `error`), Glosa monetária (calculada/não calculada), Publicação (liberada/bloqueada + motivo), Duração, e **Artefatos** com caminhos completos sem truncamento após a tabela.
4. **`total_esperado`**: igual a `aferidos` até a névoa "Validação de indicadores" graduar (não inventei 14 — contrato estável para CI).
5. **JSON (Q5)**: `competencia`, `resultado`, `codigo_saida`, `orgaos` (per-órgão `indicadores`/`glosa`/`publicable`/`motivo_publicacao`), `consolidado`, `publicacao` (`liberada`/`motivo`), `avisos`, `erros`, `duracao_ms` (wall-clock dos timestamps do estado), `caminhos`.
6. **Duração (Q4)**: soma do relógio de parede do estado (`started_at`/`finished_at` dos Commands); `0` para resultados sintéticos.

**Implementado no código** (esforço embarca execução):
- `orchestration/summary.py`: `summary_json()`, `_painel_resultado()`, `_caminhos_artefatos()`, contagens/duração de `RunResult`; `render_summary(..., output="text"|"json")`; linha de report marca `(rascunho — não publicável)`.
- `cli/run.py::run_run(..., output=)` e `cli/main.py`: flag `--output {text,json}` no `run` (default text); `_dispatch_run` passa o valor.

Testes: `tests/test_orchestration_summary.py` (painel com CÁLCULO FINANCEIRO INDISPONÍVEL + `summary_json` espelha `codigo_saida`). Suíte 258 passed; mypy limpo; ruff sem novas violações (4 pré-existentes).

Névoa graduada por esta resolução (novos tickets 08/09). Interfaces com 06 (portabilidade: o término Windows/mojibake do rich é o "box" do 06) e 05 (verbos/verbosidade).