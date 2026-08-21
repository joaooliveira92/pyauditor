# Map: pyauditor — revisão de fronteiras do pipeline (2)

Label: wayfinder:map

## Destination

Para cada fronteira entre pacotes do fluxo fim-a-fim (`config`/`categorias.yaml` → `split` → `bootstrap` → `measure` → `engine` → `orchestration` → `rom` → `excel`, mais `cli`/`interactive` como pontos de entrada), um relatório de achados julgando **apenas os contratos/dados que atravessam essa fronteira** — perda silenciosa de dados, mudança de shape/tipo não validada na travessia, suposições implícitas que um lado faz sobre a saída do outro, e fricção concreta observada no modelo de dados atual (CSV como formato de entrada, YAML como config, parsing manual — sem investigar alternativas, só registrar onde esse modelo já mostrou ser frágil). Não é revisão de qualidade interna de um pacote isolado. Termina numa síntese com punch list priorizado, mesma ordem de severidade do skill `python-production-engineer`. Este mapa produz achados, não correções — qualquer correção vira ticket/mapa de follow-up separado.

Retomada de um esforço homônimo em inglês (`pipeline-boundaries-review`, apagado em 2026-08-21 sem terminar — 5 de 7 fronteiras tinham achados, mas uma feature inteira nova, `categorias.yaml`/comando `split`, entrou no código depois daquele diagnóstico e o invalidou). Este mapa reparte do zero, sem reaproveitar os achados antigos como verdade.

## Notes

- Domínio: pyauditor — ver `CONTEXT.md` na raiz do repo para o vocabulário de negócio (órgão, competência, glosa, ROM, INMS, Categoria/Grupo executor). Os estágios do pipeline (`config`/`split`/`bootstrap`/`measure`/`engine`/`orchestration`/`rom`/`excel`) são nomes de pacote de código.
- Cada ticket deve chamar o Skill tool com `python-production-engineer` (ler `.agents/skills/python-production-engineer/SKILL.md` por inteiro) e aplicar sua ordem de severidade em "Regras de revisão de código" e a lista de "Comportamentos proibidos".
- Sem atalho greedy: cada ticket rastreia toda chamada/dado que cruza a fronteira do seu pacote (não só o arquivo maior/mais recente) antes de escrever achados.
- Achados citam `file:line`. Severidade por achado, não por pacote.
- Além de achados de contrato/shape, cada ticket que toca leitura de CSV/YAML registra fricção concreta do modelo atual (defaults silenciosos quando uma chave está ausente, caminhos/estrutura de diretório assumidos sem checagem, parsing manual sem schema) como achado com severidade — não investiga alternativas de arquitetura, só reporta o que já dói.
- As convenções deste repo (`CLAUDE.md`, `docs/agents/unslop.md`, padrões existentes) valem sobre os defaults genéricos do skill quando conflitarem.
- Não trate `.scratch/production-readiness-review` (apagado) como referência ou como "já coberto, pode pular" — este mapa parte de olhar novo, não do julgamento daquele review.

## Decisions so far

- [Config→engine boundary review](issues/01-config-engine-boundary.md) — nenhum nome de coluna declarado em YAML (`Filter.column`, `id_column`, `*_column`) é validado contra o cabeçalho real do CSV; typo vira zero silencioso (`ratio.py`/`_filters.py`) ou descarte silencioso de ocorrências (`external_catalog_sum.py`); typo na chave `indicator:` faz o INMS inteiro sumir do processamento sem aviso.
- [Engine→orchestration boundary review](issues/02-engine-orchestration-boundary.md) — a fronteira real é mediada por `cli/measure.py`, que reduz tudo a um bool; `hard_failure` ignora `conforms`/`result_pct`, então um cálculo sistematicamente quebrado não aciona nenhum sinal de falha no resumo do run; `NaN`/`Infinity` não bloqueado em `_require_numeric` confirmado de novo aqui.
- [Orchestration↔cli/interactive boundary review](issues/03-orchestration-cli-interactive-boundary.md) — `--capa-path` é respeitado por `pyauditor run`/interativo mas **ignorado** por `pyauditor bootstrap` direto (grava em `capa_<orgao>.csv` mesmo assim); resume do fluxo guiado não passa `force_commands`, painel final pode alegar "publicação liberada" sem recalcular.
- [Rom→excel boundary review](issues/04-rom-excel-boundary.md) — `_require_numeric` aceita `NaN`/`Infinity` (json.loads não bloqueia por padrão), corrompendo células/totais sem erro; `orgao` do sidecar nunca cross-checado contra o diretório de origem, um JSON mal-rotulado some silenciosamente da consolidação MinC+MTur.
- [Excel report→consolidate boundary review](issues/05-excel-report-consolidate-boundary.md) — `consolidate.py` reimplementa a fórmula de glosa do zero (ignora rollover mensal e teto por-órgão), podendo divergir do valor já oficial/publicado no relatório por-órgão; confirmado que `consolidate` nunca lê o `.xlsx` de `report.py`, ao contrário do que o próprio docstring do módulo afirma.
- [Cli dispatch boundary review](issues/06-cli-dispatch-boundary.md) — `competencia` nunca validada antes de já criar diretórios de log/output com o valor malformado; log do `split` usa convenção de saída (ROM) em vez de onde ele realmente escreve, órfão com `--orgao both`.
- [Interactive→orchestration boundary review](issues/07-interactive-orchestration-boundary.md) — confirma independentemente o gap de `force_commands` do ticket 03; `orgao` trafega como `str` livre sem o `Literal` que `cli/main.py` usa; `split`/categorias não ganhou prompt dedicado, só entrou na lista genérica de checkboxes.
- [Categoria/split boundary review](issues/08-categoria-split-boundary.md) — **candidato a P0**: `split` grava a config derivada por categoria no mesmo `config_dir` da config base; `measure` processa as duas via glob e `report.py` soma `penalty_points` sem deduplicar por `contractual_id` — glosa financeira contada em dobro para todo INMS segmentado por Categoria, contradizendo o próprio spec ("N categorias = N ROMs"). Também: modo `in_values` nunca cross-checado contra os literais reais do CSV (typo vira "zero atividade" silencioso, sem warning).

## Not yet specified

- **CSV+YAML é o modelo de dados certo para este pipeline, ou vale migrar para algo mais robusto (schemas Pydantic-first mais estritos, Parquet/DuckDB, pandas/polars como camada de ingestão)?** Pergunta grande demais para ticketar agora — depende de quanta fricção concreta os achados de fronteira (ver Notes) realmente revelarem. A síntese decide, ao final, se essa pergunta vira um mapa wayfinder de decisão arquitetural dedicado.

## Out of scope

- Qualidade de código interna a um único pacote (não-fronteira) — fora do escopo deste mapa por definição do destino, não por já ter sido coberta em outro lugar.
- Conformidade spec-vs-implementação (Termo de Referência, planilha de inspiração) — coberta por `framework-audit` (fechado).
- CI/testes como domínio próprio (flakiness de suíte, pipelines de CI) — fora de escopo; se necessário, é um mapa à parte.
- Implementar qualquer correção que os achados deste mapa revelarem — vira esforço de follow-up separado, uma vez que o punch list (ticket de síntese) existir.
- Investigar alternativas concretas ao modelo CSV+YAML — ver "Not yet specified": registrar fricção é neste mapa, avaliar alternativas não é.
