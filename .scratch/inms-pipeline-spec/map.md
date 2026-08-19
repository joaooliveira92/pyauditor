# Map: pyauditor — spec do pipeline de apuração INMS

Label: wayfinder:map

## Destination

Um `spec.md` de arquitetura — não código — pronto para outra sessão implementar. Cobre: (1) o engine genérico de apuração dos 14 indicadores INMS de SLA do contrato 40/2022 - Ministério Cultura, a partir de pares `inms-<n>.yaml` (schema declarativo) + `inms-<n>.csv` (dataset), com quality gates que falham a medição e um ROM (memória de cálculo) Markdown human-readable por indicador, incluindo contagem/motivo de linhas rejeitadas; (2) a planilha Excel final consolidada (estrutura em `docs/spreadsheet.md`) e o Excel de capa do contrato, ambos geridos por uma CLI que nunca recria a capa se ela já existir.

## Notes

- Domínio: aferição mensal de SLA/INMS de um contrato de infraestrutura de TI (Termo de Referência + Anexo D "Prazos e Níveis Mínimos de Serviço", já lido na íntegra — ver ticket 02).
- Stack não é decisão a grillar (dado pelo usuário): Python, Pydantic, `mypy --strict`, Loguru, pytest, `uv`.
- Referências primárias: `docs/termo_de_referencia/anexo_d_prazos.html` (lido), `docs/termo_de_referencia/anexo_e_desconformidade_tecnica.html` (lido — ver ticket 11, pesquisa completa em `docs/research/anexo-e-inms-1.8.md`), item 35 do Termo de Referência sobre glosa monetária (localizado em `docs/termo_de_referencia/07_modelo_de_gestao.html` — ver ticket 12, pesquisa completa em `docs/research/12-glosa-item-35.md`).
- Dados de produção reais existem em `/Users/joao/dev/pyauditor/input/` (14 pares, um por indicador) — fora do controle de versão, contêm PII (nome de solicitante/criador/técnico).
- Excel final: `docs/spreadsheet.md` (estrutura de abas) + `docs/styleguide.md` (convenção de formatação estilo IB — fonte, cores por função, bordas, etc.) — ambos servem de referência para o `spec.md`, não são doutrina rígida.
- Sessões que resolverem tickets `grilling` devem chamar o Skill tool duas vezes: "grilling" e "domain-modeling".

## Decisions so far

- [Destino e escopo do mapa](issues/01-destino-e-escopo.md) — spec.md de arquitetura (não código), cobrindo os 14 indicadores + Excel final + Excel de capa, no mesmo mapa.
- [Classificação dos 14 indicadores por shape de cálculo](issues/02-classificacao-shapes.md) — leitura do Anexo D mostrou que 10/14 cabem em `ratio` genérico (incluindo disponibilidade pré-agregada, revisado no ticket 15); restam `segmented_ratio` (1.2), `count_difference` (1.10) e `external_catalog_sum` (1.8) como shapes genuinamente divergentes.
- [Engine: strategies plugáveis + Pydantic discriminado](issues/03-engine-strategies-pydantic.md) — campo `shape` no YAML seleciona uma strategy registrada; Pydantic usa discriminated union por `shape` para tipar `calculation`/`penalty`.
- [Validação em duas camadas](issues/04-validacao-duas-camadas.md) — Pydantic cuida de schema/config (fail-fast); `QualityGateRunner` cuida de dados (fail de medição, relatório humano de rejeitados com ID e motivo).
- [Estratégia de testes e fixtures](issues/05-testes-fixtures.md) — smoke test parametrizado sobre os 14 `acceptance_test` reais dos YAMLs + fixtures sintéticas unitárias por strategy.
- [CLI em 3 subcomandos](issues/06-cli-subcomandos.md) — `bootstrap` (capa Excel idempotente) / `measure` (ROM por indicador/competência) / `report` (consolidação Excel final), mais um comando guarda-chuva opcional.
- [Contrato do ROM Markdown](issues/07-contrato-rom.md) — template genérico (cabeçalho, população, rejeições) + renderer de memória de cálculo específico por shape.
- [Escopo mono-contrato e dados fora do versionamento](issues/08-mono-contrato-dados.md) — sem abstração multi-contrato prematura; CSVs/YAMLs de produção git-ignorados (PII); fixtures sintéticas versionadas em `tests/fixtures/`.
- [Layout de pacotes e registry de strategies](issues/09-layout-pacotes.md) — `src/pyauditor/{config,engine,rom,excel,cli}`; registry de strategies como dict módulo-level, sem plugin discovery.
- [Campo órgão fixado em MinC](issues/10-campo-orgao-minc.md) — schema modela `orgao` desde já, valor fixo `"MinC"`; lógica de consolidação ponderada MinC+MTur fica fora do destino atual.
- [Revisão do shape per_asset_ratio à luz dos dados reais](issues/13-revisao-per-asset-ratio.md) — datasets reais de 1.4/1.5/1.14 são um único registro pré-agregado (não eventos brutos por ativo); `per_asset_ratio` deixa de ser uma strategy própria e vira uma variação de fonte (`aggregation: "precomputed"`) dentro de `ratio` — reduz o engine de 5 para 4 shapes.
- [Shape do INMS 1.8 (external_catalog_sum)](issues/11-research-anexo-e.md) — Anexo E é um catálogo fechado de 106 itens (`OD-01`..`OD-106`, 22 categorias, 50–20.000 pontos), soma linear sem teto/multiplicador (regra de dedup: ocorrência multi-enquadrada conta só o item de maior pontuação); suficiente para modelar o catálogo e o cálculo bruto, mas não a conversão pontos→glosa (item 35, ticket 12) nem o schema de ingestão de ocorrências (formato ITSM do `inms-001-08.csv` é plausível mas não confirmado pelas fontes primárias — fica fog).
- [Conversão de pontuação em glosa monetária](issues/12-research-glosa-item-35.md) — item 35 (`docs/termo_de_referencia/07_modelo_de_gestao.html`) define `Ajuste_NMS(%) = Σ Pontos_NMS × 0,001` (soma total de pontos de todos os INMS do mês, 1 ponto = 0,001% de glosa), teto de 30% do valor mensal com rollover para o mês seguinte; suficiente para especificar a aba GLOSAS.
- [Escrever spec.md](issues/14-escrever-spec-md.md) — spec consolidado em [`docs/spec/inms-pipeline.md`](../../docs/spec/inms-pipeline.md); destino do mapa alcançado, fog remanescente (MinC/MTur, ingestão INMS 1.8, múltiplos ativos) documentado como fora de escopo desta versão.

## Not yet specified

- Schema do dataset de origem/ingestão de ocorrências do INMS 1.8 (`external_catalog_sum`): o Anexo E não define mecanismo de coleta, e o formato ITSM genérico do `inms-001-08.csv` real é plausível mas não confirmado como o formato correto — ver ticket 11 (resolvido quanto ao catálogo/cálculo, mas deixa esta parte em fog).
- Mapeamento ROM→abas do Excel final (`INMS_BASE` e abas por grupo operacional) para o caso de segregação real MinC/MTur — hoje só existe dado MinC nos 14 datasets de produção; fica em fog até aparecer um dataset real com os dois órgãos.
- Convenção de descoberta de arquivos quando um indicador tiver múltiplos ativos/serviços pré-agregados no mesmo período (ex.: INMS 1.14 cobre 6 serviços nomeados, mas hoje só há 1 CSV por indicador em `/input`) — precisa ser especificada se/quando aparecer mais de um arquivo por indicador por competência.

## Out of scope

(nenhum item identificado até o momento)
