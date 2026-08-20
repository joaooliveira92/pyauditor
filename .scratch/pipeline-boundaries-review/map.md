# Map: pyauditor — pipeline boundaries review

Label: wayfinder:map

## Destination

Para cada pacote sob `src/pyauditor/`, um relatório de achados julgando **apenas os contratos/fronteiras de dados que esse pacote expõe ou consome de seus vizinhos no fluxo fim-a-fim** (`bootstrap` → `config` → `measure` → `engine` → `orchestration` → `rom` → `excel`, mais `cli`/`interactive` como pontos de entrada) — perda silenciosa de dados, mudança de shape/tipo não validada na travessia da fronteira, suposições implícitas que um pacote faz sobre a saída de outro. Não é uma revisão de qualidade interna de cada pacote (isso já foi feito, ver Notes). Termina numa síntese com punch list priorizado, mesma ordem de severidade do skill `python-production-engineer`. Este mapa produz achados, não correções — qualquer correção vira ticket/mapa de follow-up separado.

## Notes

- Domínio: pyauditor — ver `CONTEXT.md` na raiz do repo para o vocabulário de negócio (órgão, competência, glosa, ROM, etc.). Os estágios do pipeline (`bootstrap`/`measure`/`engine`/`orchestration`/`rom`/`excel`) são nomes de pacote de código, não termos de domínio novos.
- Cada ticket deve chamar o Skill tool com `python-production-engineer` (ler `.agents/skills/python-production-engineer/SKILL.md` por inteiro) e aplicar sua ordem de severidade em "Regras de revisão de código" e a lista de "Comportamentos proibidos".
- `.scratch/production-readiness-review/map.md` (fechado) já fez uma revisão de qualidade interna de cada pacote — não repita achados de lá. Este mapa é sobre o que atravessa a fronteira entre pacotes, não o que vive dentro de um só.
- Sem atalho greedy: cada ticket rastreia toda chamada/dado que cruza a fronteira do seu pacote (não só o arquivo maior/mais recente) antes de escrever achados.
- Achados citam `file:line`. Severidade por achado, não por pacote.
- As convenções deste repo (`CLAUDE.md`, `docs/agents/unslop.md`, padrões existentes) valem sobre os defaults genéricos do skill quando conflitarem.

## Decisions so far

- [Config→engine boundary review](issues/01-config-engine-boundary.md) — mypy clean; 3 HIGH silent-zero paths onde um nome de coluna com typo no config (`external_catalog_sum`, `precomputed_table`, `ratio` precomputed) vira falso "totalmente conforme, zero penalidade" em vez de erro, porque `engine` lê colunas via `dict.get(name, "")` sem nunca validar contra o header real do CSV; 1 unit mismatch real (`Target.value` travado em 0-100% mas reusado como limiar de pontos sem limite no modo `result_is_percent=False`); 1 gap de campo cruzado não testado (`numerator_column`/`denominator_column` opcionais independentes, desativa weighting silenciosamente); mais 2 diagnósticos enganosos em `quality_gates`/`_filters`.
- [Engine→orchestration boundary review](issues/02-engine-orchestration-boundary.md) — ver `## Answer` no ticket para o detalhe; achados sobre shape/unidade da saída do engine assumida sem revalidação por `orchestration`.
- [Rom→excel boundary review](issues/04-rom-excel-boundary.md) — 3 achados HIGH: `_require_numeric` não checa finitude, então `NaN`/`Infinity` num sidecar malformado passa a validação e `openpyxl` grava a célula como vazia sem erro, corrompendo silenciosamente os totais agregados; `IndicatorSummary` não carrega `competencia`, então um sidecar extraviado no diretório errado é indetectável; `orgao` também não é cross-checado contra o diretório de origem, permitindo que um sidecar mal-rotulado sobrescreva silenciosamente o registro do outro órgão na consolidação.
- [Excel report→consolidate boundary review](issues/05-excel-report-consolidate-boundary.md) — `consolidate.py` na verdade nunca lê as abas `INMS_BASE`/`GLOSAS` de `report.py` (reconstrói tudo a partir do ROM JSON), estreitando a fronteira real; dentro dela: o rateio MinC/MTur editado manualmente pelo fiscal em `CALCULO_PAGAMENTO` é silenciosamente sobrescrito de volta para 0.5/0.5 a cada rerun de `consolidate`; `build_capa` só avisa em caso de *divergência* entre MinC/MTur, não de *ausência* (drift de schema perde o valor em silêncio); `check_consolidate_ready` só valida existência de arquivo/diretório, nunca o shape do workbook.
- [Interactive→orchestration boundary review](issues/07-interactive-orchestration-boundary.md) — o fix de Ctrl+C (commit `6d10b1b`) fechou de fato a fronteira: `InteractionCancelled` propaga sem interceptação por todo caminho, incluindo o prompt de retry/skip/abort em `on_failure` que os testes originais não cobriam; gaps restantes são só de cobertura de teste (cancelamento em `select_commands`/`on_failure` não testado) e um gap de validação pré-existente e simétrico (campos de path livre sem validação nos dois lados de entrada, não específico desta fronteira).

## Not yet specified

(nenhuma — escopo fechado no grilling de charting: 7 fronteiras de pacote + síntese)

## Out of scope

- Qualidade de código interna a um único pacote — já coberta por `production-readiness-review` (fechado).
- Conformidade spec-vs-implementação (Termo de Referência, planilha de inspiração) — já coberta por `framework-audit` (fechado).
- Implementar qualquer correção que os achados deste mapa revelarem — vira esforço de follow-up separado, uma vez que o punch list (ticket de síntese) existir.
