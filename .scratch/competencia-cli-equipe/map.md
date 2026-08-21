---
Labels: wayfinder:map
---

# Mapa: competência da CLI, filtro de período e equipe.csv

## Destination

Spec pronta para implementar em `.scratch/competencia-cli-equipe/spec.md`: o pipeline deriva Competência e Período inicial/final da aferição exclusivamente da competência obrigatória da CLI, filtra todo dataset ao período da aferição (WARN se zero linhas no período; descarte com log INFO se misto) e preenche os responsáveis da planilha xlsx a partir de `input/equipe.csv`.

## Notes

Domínio: pipeline de aferição pyauditor — glossário em `CONTEXT.md`.
Skills de sessão: chamar `grilling` + `domain-modeling` em todo ticket HITL.
Decisões tomadas no charting (2026-08-21, aprovadas pelo humano; não reabrir sem ele):

- **Período é da CLI, sempre**: competência posicional obrigatória; nunca inferida de dados nem lida da capa. A coluna de período de cada dataset é declarada explicitamente no YAML do indicador — indicador filtrável sem declaração é erro de configuração, não filtro silencioso.
- **Zero linhas no período**: WARN e segue. Dataset misto: descarta as linhas fora do período com log INFO (contagem).
- **Capa**: campos Competência/Períodos saem de `ORGAO_FIELD_LABELS`; `validate_periodo_competencia` deletada com seus testes; capa antiga que ainda tenha esses campos: ignorar.
- **ROM**: cabeçalho usa valores derivados da CLI; nota de proveniência passa a dizer que são derivados do argumento.
- **equipe.csv**: lido pelo `report`; titulares viram `"Nome (SIAPE)"` nos 4 campos de responsáveis; substitutos ficam só no CSV; ausente/malformado → warning, campos vazios (padrão `objetos.csv`).
- **Filtro**: um único ponto na leitura do dataset; split, measure, sintetico.xlsx e acceptance tests herdam.

## Decisions so far

- [Onde mora o filtro de período e como o YAML o declara](issues/01-filtro-periodo-design.md) — módulo `periodo.py` canônico; filtro puro chamado por split/measure/sintetico; `source.period_column` exigido na execução; fora da janela sempre descartado; `--strict` descarta linha sem prova de período (default mantém pra quality gates); interativo herda.
- [Enterro dos campos de período na capa e ROM derivado](issues/02-enterro-capa-e-rom.md) — ROM recebe `competencia`/`periodo` explícitos; planilhas mantêm rótulos canônicos com valores da CLI; nota de proveniência aprovada; publicação não depende mais de período.
- [equipe.csv alimenta os responsáveis do xlsx](issues/03-equipe-csv-xlsx.md) — fonte única `excel/equipe.py` (padrão objetos.py) para capa embutida, consolidado e ROM; célula "Nome (SIAPE)"; bootstrap cria esqueleto com as 8 funções; substitutos só no CSV.
- [Semântica fina dos avisos do filtro](issues/04-semantica-avisos-filtro.md) — WARN de janela vazia 1× por (órgão, bruto), emitido por split ou measure-whole_indicator; INFO estruturado de descarte; dataset vazio de fábrica não avisa; ROM declara "Fora do período descartadas"; sidecar ganha contagens opcionais.
- [Escrever a spec da competência da CLI](issues/05-escrever-spec.md) — spec completa em [spec.md](spec.md), destino do mapa atingido: nada restou a decidir antes de implementar.

## Not yet specified

(nada — a rota está clara)

## Out of scope

- Renomear/reestruturar colunas dos CSVs brutos do fornecedor — o formato é dado pelo fornecedor; o pipeline se adapta via declaração no YAML.
- Estender `--strict` para além das linhas sem prova de período.
- Capa enxuta vs template — pendência sua, adjacente a este mapa: sua capa real só tem Órgão/OS/SEI/Versão, mas o template ainda lista hand-fills (nota fiscal, datas da análise, Situação geral da aferição) que gateiam publicação. Se quiser resolver, é esforço novo, não retomada deste.
