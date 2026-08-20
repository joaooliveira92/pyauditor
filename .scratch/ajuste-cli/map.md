# Map: pyauditor — ajuste da saída da CLI pós-revisão

Label: wayfinder:map

## Destination

A saída do pyauditor (`run`/`report`/`consolidate`) ajustada conforme a revisão `.scratch/ajuste-cli/review.md` — mudança feita **em lugar** (no código), não só planejada. No fim: nenhuma saída — resumo, logs, células Excel ou código de saída — pode apresentar um resultado incompleto como resultado financeiro válido. Cobre os quatro eixos da revisão, nesta ordem de prioridade: semântica/corretude, resumo final acionável, observabilidade, exibição/portabilidade.

## Notes

- **Domínio**: contrato 40/2022 MinC/MTur — aferição INMS 1.1–1.14 por competência. Vocabulário em `CONTEXT.md` (glosa, sugestão de glosa, decisão fiscal, anistia, ROM, capa). Glosa nunca é silenciosa; "não calculada" ≠ `0.00`.
- **Fontes de entrada (diretriz nova)**: abandonar as capas Excel `.xlsx` (`capa.xlsx`, `capa_MinC.xlsx`, `capa_MTur.xlsx`). As entradas passam a ser CSVs: `objetos.csv` (fonte do valor monetário por item contratual) + `capa.csv` (campos comuns) + `capa_MinC.csv`/`capa_MTur.csv` (campos por órgão). Valores monetários saem das capas; comuns ficam só em `capa.csv`. Migração decide no ticket 07.
- **Skills por sessão**: grilling + domain-modeling por padrão; `prototype` para o resumo final; nenhuma research prevista (as perguntas de regra são decisões da equipe, não fatos externos).
- **Preferências do esforço**: execução embarca no mapa — ticket resolvido aciona a mudança no código. Texto de usuário permanece pt-BR. Códigos de saída importam para CI/workers. Testes cobrem os cenários da seção "Cenários de teste" do review. Manter as convenções do repo: type-checked, dataclasses frozen, atomic_write, logger estruturado.
- **Onde está a revisão**: o texto completo da avaliação (8 achados, prioridades, perguntas de equipe, cenários de teste) vive em `.scratch/ajuste-cli/review.md`.

## Decisions so far

<!-- o índice — uma linha por ticket fechado -->

- [01 - Representação da glosa não calculada](issues/01-representacao-glosa-nao-calculada.md) — `não calculada` (fato, não `indisponível`/`pendente`), motivo como dado `motivo=valor mensal ausente`; células monetárias vazias + célula de status (nunca `0.00`); `%Ajuste` sempre calculado (independente do valor — TR); `0.00` legítimo permanece numérico (status distingue); log `consolidate`/resumo final carregam o status. Fonte monetária deixa de ser a capa — `objetos.csv` passa a ser a fonte (ticket 07).
- [02 - Criticidade dos campos da capa](issues/02-criticidade-campos-capa.md) — nenhun campo obrigatório para processar (o pipeline processa com capa incompleta e marca o resultado); **obligatorios para publicar/assinar**: Períodos, Fiscais (técnico, administrativo, requisitante), Gestor, Situação ≠ "Em preenchimento" + campos comerciais de `capa.csv`; **opcionales/informativos**: Número de OS, NF/data, Data da análise, Versão da planilha. Competência derivada do argumento CLI; períodos derivados; divergencia de capa → WARNING (03). Estado "rascunho"/"não-publicable" existe para capa incompleta.
- [03 - Contrato de códigos de saída](issues/03-contrato-codigos-saida.md) — tabela completa: `0` CONCLUÍDO, `1` FALHA, `2` USO INVÁLIDO (exclusivo do parse), `3` CONCLUÍDO COM PENDÊNCIAS (rascunho/não-publicável + etapa de produção skipped), `4` CÁLCULO FINANCEIRO INDISPONÍVEL (glosa não calculada). Escopo `run`/`report`/`consolidate`; `bootstrap`/`measure` ficam `0`/`1`. Precedência global agregada por órgão `1>4>3>0`; warnings não bloqueiam; `3` é balde único, detalhamento no resumo (04). Rótulos estáveis em `cli/results.py::_EXIT_NAMES`. **Implementado no código**: `ReportResult.publicable`/`glosa_calculada`, `ConsolidateResult.glosa_calculada`, `exit_code_for_run` com a precedência, dispatch de `consolidate` flag-aware.
- [04 - Resumo final acionável](issues/04-resumo-final-acionavel.md) — painel "Resultado" (resultado/competência/órgãos/indicadores/relatórios `N (K rascunho)`/consolidado/avisos e erros reais/glosa/publicação/duração) + bloco Artefatos com caminhos completos; `--output json` no `run` (mesmo estado global do código, p/ CI); duração = wall-clock dos timestamps do estado; `total_esperado` = `aferidos` até a névoa de validação graduar. Protótipo capturado na branch `prototype/resumo-final` (commit `dc63f6b`). **Implementado no código**: `summary_json`, `_painel_resultado`, flag `--output {text,json}` no `run`.
- [05 - Logs dos indicadores e observabilidade](issues/05-logs-indicadores-observabilidade.md) — evento por indicador `indicador apurado: orgao= codigo= rom_path= status=`; padrão INFO **sem** linha por indicador (conciso `MinC: 14/14` por órgão), `-v` DEBUG por indicador, `-vv` detalhes, `--log-level` manual prevalece, `--log-format json` estrutura o stderr (`serialize=True` do loguru, `record.extra`); `--log-format` é **separado** de `--output json` (04). Flags em todos os subcomandos. **Implementado**: `log_event`, `resolve_log_level`, flags `-v`/`--log-level`/`--log-format`; eventos em measure/bootstrap/report/consolidate; corrige o achado §3 ("capa existente será reutilizada").
- [06 - Exibição e portabilidade de caminhos](issues/06-exibição-e-portabilidae-de-caminhos.md) — portabilidade "não quebrar" (pathlib em tudo, sem `\` fixo); formato humano pt-BR (`46.909,85`) **só no painel** vs. ponto decimal em logs/JSON; `fmt_pt_br()` helper; painel ganhou `Total de pontos (consolidado)`. **Implementado**: `ConsolidateResult.total_pontos`, `fmt_pt_br`, log `glosa` `.2f` (máquina).
- [07 - Migração das capas .xlsx para CSV + objetos.csv como fonte de valores](issues/07-migracao-capas-csv-objetos.md) — abandono das capas Excel; **entradas = CSVs**: `capa.csv` (campos comuns: número do contrato, SEI, empresa, CNPJ, objeto, vigência) + `capa_{orgao}.csv` (por órgão: órgão, competência, períodos, fiscais, gestor, versão, situação; monetários **fora**) + `objetos.csv` (fonte do monetário: TOTAL MENSAL + itens por índice; Σ e ×12 → warning). `bootstrap` cria os 3 CSVs; `--capa-path` = capa.csv comum, por-órgão deriva do mesmo diretório (Q6/Q9). **Implementado**: `excel/objetos.py` (`read_objetos`, `parse_brl_value`), `excel/capa.py` (`bootstrap_capa_csv`, `read_capa_csv_fields`, `COMMON/ORGAO_FIELD_LABELS`), merge capa comum+órgão, `valor_base` de `objetos.csv` em report/consolidate, `Valor Mensal (R$)` em SERVICOS. Ausente = incompleto; malformado = FALHA (exit 1).

## Not yet specified

- **Validação de indicadores**: "O número de indicadores esperado é sempre 14? Uma execução com 13 ainda gera relatório? Há validação de duplicidade de códigos?" — gradua quando a fronteira alcançar a camada de `measure` (o ticket 05 cobre logs disso).
- **Trilha de auditoria das decisões preservadas**: o que conta como "decisão", onde fica armazenada, e o teste de regressão garantindo que decisões manuais não são perdidas na reescrita do consolidado.

## Out of scope

<!-- work beyond the destination — fechado, nunca gradua -->