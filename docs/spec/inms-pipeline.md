# Spec: pipeline de apuração INMS (contrato 40/2022 — Ministério da Cultura)

> Arquitetura, não implementação. Consolida as decisões travadas no mapa Wayfinder
> [`.scratch/inms-pipeline-spec/map.md`](../../.scratch/inms-pipeline-spec/map.md) (tickets 01–13);
> escrito pelo ticket 14. Pronto para outra sessão implementar.

## 1. Visão geral e destino

O `pyauditor` apura mensalmente os 14 indicadores INMS de SLA do contrato 40/2022 (Anexo D — Prazos
e Níveis Mínimos de Serviço) a partir de pares declarativos `inms-<n>.yaml` (schema/config) +
`inms-<n>.csv` (dataset), produz uma memória de cálculo (ROM) Markdown por indicador com quality
gates que podem falhar a medição, e consolida tudo numa planilha Excel final mais um Excel de capa
do contrato, geridos por uma CLI.

O engine é genérico o bastante para qualquer YAML aderente ao schema — os indicadores que não
divergem estruturalmente do INMS 1.1 (razão simples × 100, meta + penalidade em degrau) não exigem
decisão nova de arquitetura, só configuração. Ver [Ticket 01](../../.scratch/inms-pipeline-spec/issues/01-destino-e-escopo.md).

## 2. Classificação dos 14 indicadores por shape

Leitura integral do Anexo D (Tabela 28) mais inspeção dos 14 CSVs reais em `/input` reduziram o
engine a **4 shapes**:

| Shape | Indicadores | Descrição |
|---|---|---|
| `ratio` (`aggregation: count_distinct \| sum \| precomputed`) | 1.1, 1.3, 1.4, 1.5, 1.6, 1.7, 1.9, 1.11, 1.12, 1.13, 1.14 | numerador/denominador × 100, meta com operador de comparação (`>=`/`<=`), penalidade em degraus |
| `segmented_ratio` | 1.2 | 3 sub-razões por categoria (prioridade Alta/Média/Baixa), cada uma com meta e taxa de penalidade próprias; penalidade final = soma das 3 |
| `count_difference` | 1.10 | `CNI = QRC − QCSI` (diferença de contagem, não razão); penalidade fixa por unidade faltante |
| `external_catalog_sum` | 1.8 | soma de pontos de um catálogo externo fechado (Anexo E), sem meta percentual |

Detalhe por variação de `ratio`:

- `count_distinct` — numerador/denominador contados a partir de linhas do CSV (ex.: 1.1, 1.6, 1.7,
  1.9, 1.11, 1.12, 1.13).
- `sum` — razão de somas de dias/tempo, não contagem distinta (ex.: 1.3).
- `precomputed` — numerador/denominador já vêm prontos de uma ferramenta de monitoramento externa;
  um YAML+CSV = um ativo/serviço = uma medição independente (ex.: 1.4, 1.5, 1.14 — ver §3.1).
- `target.operator` cobre metas invertidas (ex.: 1.11 é "≤").

Fonte: [Ticket 02](../../.scratch/inms-pipeline-spec/issues/02-classificacao-shapes.md),
[Ticket 13](../../.scratch/inms-pipeline-spec/issues/13-revisao-per-asset-ratio.md).

### 2.1 Revisão `per_asset_ratio` → `ratio(aggregation=precomputed)`

Os CSVs reais de 1.4/1.5/1.14 são um único registro pré-agregado por indicador
(`Descrição, Disponibilidade Esperada (%), Disponibilidade Realizada (%), ...`), não eventos brutos
por ativo. "Para cada um dos sistemas/serviços, utilizar a fórmula ao lado" (Anexo D) significa, na
prática, **múltiplos pares YAML+CSV** — um por ativo/serviço — cada um tratado como uma medição
`ratio` normal, não uma agregação interna multi-ativo dentro de um único CSV. Isso eliminou a
strategy `per_asset_ratio` que o Ticket 02 havia proposto antes de ver os dados reais.

### 2.2 INMS 1.10 — schema de preenchimento manual provisório

Como o INMS 1.8 (§11.3), o Anexo D não define como um controle de segurança recomendado/implantado
é registrado no dataset de origem, e o `/input/inms-001-10.csv` real está vazio. Schema provisório
adotado, mapeando direto nos campos já existentes de `count_difference`
(`recommended_filter`/`implemented_filter`): um CSV com uma linha por controle recomendado, colunas
`ID_Controle`, `Framework` (referência ao framework acordado com a CONTRATADA — Anexo D menciona que
isso "será acordado", sem fixar um framework específico), `Descricao` (texto livre) e `Implantado`
(`S`/`N`). `QRC` = total de linhas aceitas pelos quality gates; `QCSI` = subconjunto com
`Implantado = S`. Exemplo completo em
`tests/fixtures/manual_entry_examples/inms-1.10-{config.yaml,controles.csv}`, verificado em
`tests/test_manual_ingestion_inms_1_10.py`. Revisar se/quando a fiscalização identificar um sistema
real de acompanhamento de controles de segurança.

## 3. Contratos Pydantic por shape

Campo `shape` explícito no YAML seleciona uma strategy registrada (strategy/registry pattern) — um
único fluxo de execução para os 14 indicadores: `load config → valida quality_gates → aplica
strategy → gera ROM`.

Pydantic usa **discriminated union pelo campo `shape`**: cada strategy declara seu próprio modelo
para os blocos `calculation`/`penalty` do YAML (`RatioCalculation`, `SegmentedRatioCalculation`,
`CountDifferenceCalculation`, `ExternalCatalogSumCalculation`), com `mypy --strict` garantindo que
cada strategy só recebe o shape de config que sabe processar — sem `dict[str, Any]` nem
`# type: ignore` espalhados pelo engine.

```python
Calculation = Annotated[
    RatioCalculation | SegmentedRatioCalculation | CountDifferenceCalculation | ExternalCatalogSumCalculation,
    Field(discriminator="shape"),
]
```

Fonte: [Ticket 03](../../.scratch/inms-pipeline-spec/issues/03-engine-strategies-pydantic.md).

## 4. Validação em duas camadas

- **Pydantic** — "isso é um YAML/config válido?" (schema errado, coluna obrigatória ausente na
  declaração). Fail-fast, erro de programador/config, antes de ler o CSV.
- **`QualityGateRunner`** — "esses dados batem com as regras de negócio declaradas?"
  (`quality_gates.checks` do YAML). Fail de medição; roda depois do parse do CSV e antes do
  cálculo; produz os "rejeitados com ID e motivo" que alimentam o ROM.

Manter as camadas separadas preserva, no ROM, a distinção entre "config quebrada" e "dado
rejeitado". Fonte: [Ticket 04](../../.scratch/inms-pipeline-spec/issues/04-validacao-duas-camadas.md).

## 5. Estratégia de testes

- **Smoke test parametrizado** (`pytest.mark.parametrize`) sobre todos os `acceptance_test`
  encontrados nos 14 pares yaml+csv de produção — garante que a spec bate com a realidade
  contratual.
- **Fixtures sintéticas unitárias por strategy** — cada strategy divergente (`segmented_ratio`,
  `count_difference`, `external_catalog_sum`) ganha testes com fixtures pequenas, sintéticas
  (nunca cópia crua de CSV de produção, ver §8), cobrindo casos de borda isolados do dado real.

Fonte: [Ticket 05](../../.scratch/inms-pipeline-spec/issues/05-testes-fixtures.md).

## 6. Contrato da CLI

**3 subcomandos explícitos**, mais um comando guarda-chuva opcional que os chama em sequência:

| Comando | Responsabilidade |
|---|---|
| `bootstrap` | cria o Excel de capa do contrato (gestor, SEI, etc.) se não existir; **idempotente** — nunca recria se já existir |
| `measure <competência>` | roda os indicadores configurados para a competência, gera um ROM Markdown por indicador |
| `report <competência>` | lê os ROMs + Excel de capa, gera a planilha Excel final consolidada |

Motivo da separação: o fiscal técnico pode precisar rodar `measure` várias vezes num mês (novos
CSVs chegando) sem reconsolidar toda vez; separar as fases facilita testar cada uma isoladamente.

Fonte: [Ticket 06](../../.scratch/inms-pipeline-spec/issues/06-cli-subcomandos.md).

## 7. Contrato do ROM Markdown

> **Nota (2026-08, `.scratch/melhoria_rom/map.md`):** as seções fixas e o
> exemplo abaixo são o desenho **original** (ticket 07) — mantidos aqui como
> histórico da decisão. O template **atual**, com seção de Identificação
> (proveniência/capa), "Linhas aprovadas pelo quality gate" (renomeado de
> "População"), Ressalva interpretativa condicional e "Pontuação apurada"
> (renomeado de "Penalidade"), está documentado em `portal/reference/rom.md`.

Um **template genérico** + um **renderer por shape** só para a seção de memória de cálculo.

Seções fixas (vêm do `QualityGateRunner`, idênticas para todo indicador):

1. **Cabeçalho** — `indicator.id`, `contractual_id`, competência, contrato.
2. **População** — filtros de escopo aplicados, contagem inicial.
3. **Rejeições** — tabela ID + motivo + regra de `quality_gates` violada.
4. **Memória de cálculo** — a única seção que varia por shape (ver abaixo).
5. **Resultado vs meta, penalidade.**

Renderer por shape:

- `ratio` — numerador/denominador únicos.
- `segmented_ratio` — sub-linhas por categoria + soma.
- `count_difference` — os termos da diferença (`QRC`, `QCSI`, `CNI`).
- `external_catalog_sum` — lista de ocorrências com pontos (código do catálogo, descrição, pontos,
  regra de maior-pontuação-vence quando aplicável — ver §11).

Gerar templates completos por shape duplicaria ~80% do conteúdo; por isso um template genérico com
um ponto de extensão por shape. Fonte: [Ticket 07](../../.scratch/inms-pipeline-spec/issues/07-contrato-rom.md).

### 7.1 Exemplo renderizado — `ratio` (INMS 1.1)

```markdown
# ROM — INMS 1.1 (Incidentes atendidos dentro do prazo)

**Contrato:** 40/2022 — Ministério da Cultura
**Competência:** 06/2026

## População
- Linhas lidas: 812
- Linhas após filtro de escopo: 798

## Rejeições
| ID | Motivo |
|---|---|
| 87091 | `DataHoraFim` nulo com `No prazo = S` |

## Memória de cálculo
- Numerador (atendidos no prazo): 750
- Denominador (total aplicável): 797
- Resultado: 94,10%

## Resultado vs meta
- Meta: ≥ 95%
- Resultado: 94,10% — **não conforme**
- Penalidade: 116,00 pontos (ver `penalty` do YAML)
```

> **Nota (pós-ticket 02/04):** a penalidade do Anexo D é uma fórmula linear contínua —
> `base_points + (meta − resultado) ÷ step_size_pct × step_points`, sem arredondamento/teto por
> degrau — confirmada pela fórmula explícita do INMS 1.2 (`(META − resultado) ÷ 0,1 × pontos`). Uma
> leitura inicial de "degrau" como valor inteiro discretizado (ceiling) foi corrigida durante a
> implementação da ticket 04; ver [Ticket 02](../../.scratch/inms-pipeline/issues/02-ratio-shape-tracer-bullet.md)
> e [Ticket 04](../../.scratch/inms-pipeline/issues/04-segmented-ratio-shape.md) no mapa de
> implementação.

### 7.2 Exemplo renderizado — `external_catalog_sum` (INMS 1.8)

```markdown
# ROM — INMS 1.8 (Ocorrências de Desconformidade Técnica)

## Memória de cálculo
| Ocorrência | Item Anexo E | Descrição | Pontos |
|---|---|---|---|
| OC-014 | OD-52 | Cabo de rede solto | 100 |
| OC-019 | OD-01 | Perda de dados críticos | 20.000 |

- Σ Pontos_NMS(1.8) = 20.100
```

## 8. Estrutura do repositório, dados de produção vs fixtures

- **Mono-contrato, sem abstração prematura.** `scope.contract` é valor fixo no YAML; "múltiplos
  contratos" seria só "múltiplos diretórios de config" no futuro — não exige decisão hoje.
- **Dados de produção fora do versionamento.** Diretório configurável, git-ignorado (hoje
  `/Users/joao/dev/pyauditor/input/`) — os 14 CSVs têm nome/solicitante/criador/técnico (PII real);
  versioná-los arrisca vazar dados pessoais no histórico do git.
- **Fixtures de teste no repo** (`tests/fixtures/`), sempre sintéticas ou anonimizadas — nunca
  cópia crua do CSV de produção.

Fonte: [Ticket 08](../../.scratch/inms-pipeline-spec/issues/08-mono-contrato-dados.md).

## 9. Layout de pacotes e registry de strategies

```python
src/pyauditor/
├── config/        # modelos Pydantic, discriminated union por `shape`
├── engine/
│   ├── quality_gates.py   # QualityGateRunner
│   └── strategies/         # ratio, segmented_ratio, count_difference, external_catalog_sum
├── rom/            # renderização Markdown (template genérico + renderer por shape)
├── excel/          # builder da planilha final + capa (usa docs/spreadsheet.md e docs/styleguide.md)
└── cli/            # bootstrap / measure / report (+ comando guarda-chuva)
```

Registry de strategies: **dict módulo-level**
(`SHAPE_REGISTRY: dict[str, type[CalculationStrategy]]` em `engine/strategies/__init__.py`),
populado por import explícito de cada strategy — sem `entry_points`/plugin discovery (mono-repo,
strategies fixas e conhecidas, nunca vêm de fora do repo).

Fonte: [Ticket 09](../../.scratch/inms-pipeline-spec/issues/09-layout-pacotes.md).

## 10. Modelagem do campo `orgao`

Os 14 CSVs reais de produção não têm segregação MinC/MTur — todo registro com campo `Contrato`
mostra apenas `"40/2022 - Ministério Cultura"`, contradizendo a estrutura de `docs/spreadsheet.md`
(que assume ambos os órgãos desde o início).

Decisão original: **modelar o campo `orgao` desde já no schema, com valor fixo `"MinC"`** — evita
retrabalho de schema quando/se aparecer dado de MTur. Fonte:
[Ticket 10](../../.scratch/inms-pipeline-spec/issues/10-campo-orgao-minc.md).

**Atualização:** `orgao` aceita `"MinC"` e `"MTur"`, e `report` consolida os dois quando ambos
medem o mesmo indicador (mesmo `contractual_id`, mesmo `asset` — ver §2.1's `Indicator.asset`),
usando a fórmula ponderada de `docs/spreadsheet.md`:
`(Numerador MinC + Numerador MTur) / (Denominador MinC + Denominador MTur)`. A linha consolidada é
adicionada só em `INMS_BASE` (`orgao: "Consolidado"`), ao lado das duas linhas originais por
órgão — as abas de grupo operacional e `GLOSAS` continuam usando as medições originais, sem
duplicar penalidade. A penalidade da linha consolidada é a soma direta das penalidades já apuradas
por órgão (o Termo de Referência não define uma fórmula própria para isso). Nenhum dataset real de
MTur existe ainda em `/input`; provado com fixtures sintéticas em
`tests/test_orgao_consolidation.py`.

**Exceção que permanece fog:** para os indicadores de disponibilidade por ativo (1.4, 1.5, 1.14),
`docs/spreadsheet.md` exige "a fórmula específica prevista no Termo de Referência" em vez da
fórmula padrão — essa fórmula não foi localizada em nenhuma fonte primária lida. `report` não
consolida esses 3 indicadores; se ambos os órgãos aparecerem, mostra uma linha por órgão sem
combiná-las.

## 11. INMS 1.8 — `external_catalog_sum`

Fonte: Anexo E (`docs/termo_de_referencia/anexo_e_desconformidade_tecnica.html`), pesquisa completa
em [`docs/research/anexo-e-inms-1.8.md`](../research/anexo-e-inms-1.8.md).
[Ticket 11](../../.scratch/inms-pipeline-spec/issues/11-research-anexo-e.md).

### 11.1 Catálogo

Tabela 29 "Itens de Desconformidade Técnica": 106 itens (`OD-01`..`OD-106`), 22 categorias
(`ASSUNTO`). Colunas: `ID`, `ASSUNTO`, `DESCRIÇÃO`, `REFERÊNCIA` (unidade de contagem — varia por
item: "por ocorrência", "por dia de atraso", "por solução", "por Item de Configuração", "por
produto", "por evento"), `PONTUAÇÃO` (50 a 20.000 pontos por item).

Modelagem: catálogo Pydantic fixo (106 itens), carregado de um arquivo próprio do YAML/config — não
derivado do Anexo D em runtime.

### 11.2 Cálculo

Soma linear simples, sem teto e sem multiplicador por reincidência:

```
INMS 1.8 = Σ Pontos_NMS(item correspondente)
```

Única regra de ajuste: se uma ocorrência se enquadra em mais de um item do catálogo, conta apenas o
item de **maior pontuação** (dedup por ocorrência, não por período).

### 11.3 Dataset de origem — fog explícito

O Anexo E **não define nenhum mecanismo de coleta/registro** — é puramente um catálogo código →
descrição → pontos. O formato ITSM do `inms-001-08.csv` real (mesmo header de tickets de chamado
usado pelos indicadores `ratio`) é **plausível mas não confirmado**: vários itens do catálogo (cabo
solto, vestimenta inadequada, ausência de pentest, desatualização de CMDB) são achados de
inspeção/auditoria, não eventos de chamado. Nada no Anexo D ou E define como uma ocorrência de
desconformidade é registrada no dataset de entrada.

**Esta spec modela o catálogo e o cálculo bruto do 1.8, mas não fecha o schema do dataset de
entrada** — tratar como pergunta em aberto para a equipe de fiscalização antes da implementação,
não assumir o CSV ITSM atual como autoritativo (ver §13).

**Schema de preenchimento manual provisório** — não uma resposta à pergunta acima, só um jeito de
começar a registrar ocorrências enquanto ela fica em aberto: um CSV com uma linha por ocorrência,
colunas `ID_Ocorrencia` (identificador livre), `Data`, `Descricao` (texto livre, não consumido pelo
cálculo) e `Codigos_Anexo_E` (um ou mais códigos `OD-NN` separados por vírgula, para o caso de
multi-enquadramento). Mapeia direto nos campos já existentes de `external_catalog_sum`
(`occurrence_id_column`/`catalog_codes_column`), sem exigir mudança de engine. Exemplo completo em
`tests/fixtures/manual_entry_examples/inms-1.8-occurrences.csv` +
`tests/fixtures/manual_entry_examples/inms-1.8-config.yaml`, verificado em
`tests/test_manual_ingestion_inms_1_8.py`. Revisar este schema se/quando a fiscalização confirmar um
formato de exportação real.

## 12. Glosa monetária (aba `GLOSAS`)

Fonte: item 35 do Termo de Referência (`docs/termo_de_referencia/07_modelo_de_gestao.html`,
seção "Sanções Administrativas e Procedimentos para retenção ou glosa no pagamento", linhas
~196–260 e ~893–1060), pesquisa completa em
[`.scratch/inms-pipeline-spec/research/12-glosa-item-35.md`](../../.scratch/inms-pipeline-spec/research/12-glosa-item-35.md).
[Ticket 12](../../.scratch/inms-pipeline-spec/issues/12-research-glosa-item-35.md).

### 12.1 Fórmula

```
Ajuste_NMS(%) = min(30%, Σ Pontos_NMS(mês) × 0,001%)
valor da glosa = Ajuste_NMS(%) × valor-base
```

- 1 ponto de penalidade = 0,001% de glosa sobre o pagamento mensal.
- A pontuação usada é o **somatório de todos os `Pontos_NMS` do mês** — todos os 14 INMS (Anexos D
  e E combinados) — somados primeiro; o percentual é calculado uma única vez sobre o total, não por
  indicador.
- **Fórmula linear contínua, sem degraus.**
- **Teto de 30%** do valor total mensal; o excedente rola para a fatura do mês seguinte (exceto no
  último mês de vigência). Ultrapassar o teto 3× em 6 meses caracteriza inexecução parcial do
  contrato.

### 12.2 Ressalvas documentadas (não bloqueiam a spec)

- Uma segunda fórmula na mesma seção do TR usa os termos `RB` e `Desconto Máximo Anual`, não
  definidos em nenhum outro lugar do documento — aparenta ser boilerplate de template genérico de
  contrato regulatório (o rótulo "Anual" destoa do resto do item, inteiramente mensal). **Não deve
  ser tratada como fonte de verdade operacional.**
- Fica ambíguo se "valor-base" é o valor total mensal do contrato ou por item/Ordem de Serviço (o
  texto usa ambos "pagamento mensal" e "PM_por_item"). **Convenção adotada por esta spec: valor
  total mensal** (é o termo usado explicitamente nas regras de teto) — não bloqueia a
  implementação.

### 12.3 Aba `GLOSAS` (colunas mínimas cobertas pela fórmula acima)

`competência`, `Σ Pontos_NMS do mês`, `percentual de ajuste`, `valor-base`, `valor da glosa`,
`teto atingido? (S/N)`, `saldo rolado para o mês seguinte`. As demais colunas de
`docs/spreadsheet.md` §Aba 10 (`faixa de descumprimento`, `reincidência`, `justificativa`, etc.) são
de preenchimento manual do fiscal, fora do cálculo automático.

## 13. Excel final e Excel de capa

Referência estrutural: [`docs/spreadsheet.md`](../spreadsheet.md) (abas) e
[`docs/styleguide.md`](../styleguide.md) (formatação — fonte, cores por função, bordas). Ambos
servem de referência, não são doutrina rígida: nem toda aba proposta em `docs/spreadsheet.md` é
sustentada pelos dados reais de produção hoje (ver §10 e fog abaixo).

- **`bootstrap`** gera a aba `CAPA_E_CONTROLE` (idempotente — ver §6).
- **`report`** consolida os ROMs Markdown gerados por `measure` na aba `INMS_BASE` e nas abas por
  grupo operacional (`ATENDIMENTO_N1`, `MONITORAMENTO_NOC_SOC`, `ATENDIMENTO_N2`, `OPERACAO_N3`),
  com segregação e consolidação MinC/MTur em `INMS_BASE` (§10) — grupos e `GLOSAS` continuam usando
  as medições por órgão sem combiná-las.
- **`GLOSAS`** é preenchida pela fórmula do §12.

## 14. Segmentação por Categoria/Grupo executor

Addendum que estende esta spec (nenhuma decisão abaixo invalida as anteriores) — origem:
`.scratch/inms-segmentacao-categoria/` (mapa e tickets 01–08). Cobre: o modelo de segmentação de
INMS em Categorias derivadas da coluna `Grupo_executor` do CSV bruto do fornecedor, a nova etapa
`split` que materializa CSVs filtrados antes do `measure` (que fica 100% inalterado), o novo
relatório xlsx "sintético" por INMS, e a composição com o fog de multi-ativo (§ acima, item 3 da
lista atualizada) e de ingestão manual (§2.2, §11.3).

### 14.1 Modelo — Categoria como filtro pré-engine

`Categoria` (ver `CONTEXT.md`) é um agrupamento de negócio de um INMS definido por um filtro sobre
`Grupo_executor`, aplicado **antes** do `measure`: o CSV bruto do fornecedor (já filtrado por
período+INMS) é recortado em N CSVs, um por categoria, cada um alimentando o `measure` existente
sem nenhuma mudança de shape ou de meta contratual — a meta continua a mesma do Anexo D.

- Um INMS pode pertencer a N categorias; cada categoria de um INMS gera **uma medição
  independente** (seu próprio ROM) — N categorias = N ROMs para aquele INMS/competência.
- **`Operação e Sustentação da Infraestrutura de TI`** (`OPERACAO_N3`) é catch-all por regra
  literal: captura todo `Grupo_executor` que contém a substring `(CIT)` e não está reivindicado
  pelas listas explícitas das outras categorias daquele INMS/órgão.
- **`outros`** é uma 4ª categoria automática e contábil: captura linhas que não batem em nenhuma
  categoria substantiva declarada. É contada (inclusive no xlsx sintético, §14.4) mas não entra no
  cálculo de conformidade/meta — existe para que nenhuma linha do dataset do fornecedor desapareça
  sem explicação.
- Categoria sem linhas no período é normal: gera medição com população zero, mesmo tratamento do
  quality gate de zero-atividade já existente — não trava o pipeline.
- **Ausência de dataset de entrada para um INMS numa competência = "não ativado", não erro** —
  regra geral do engine (vale para qualquer um dos 14 indicadores, não uma lista fechada; 1.3, 1.8 e
  1.10 são os candidatos mais prováveis na prática, por serem "sob demanda"). Fica explícito em dois
  lugares: no log do CLI (só `measure`, que é quem descobre a ausência — ver §14.4) e no xlsx
  sintético (§14.4).
- **Literais de `Grupo_executor` novos, não previstos em `categorias.yaml`**, caem em `outros`
  (contábil) e disparam um `WARNING` proativo no log de `split` — não há processo de revisão
  periódica separado; a revisão é atrelada à cadência mensal já existente do pipeline (ver §14.4
  para o texto exato).

### 14.2 Mapeamento declarativo — `configs/<orgao>/categorias.yaml`

Um arquivo por órgão (`configs/MinC/categorias.yaml`, `configs/MTur/categorias.yaml`), ao lado do
manifesto já existente `configs/<orgao>/datasets.yaml` — os literais de `Grupo_executor` diferem
entre MinC e MTur, então um arquivo por órgão é obrigatório, não estilístico. Chaves de topo por
categoria; cada entrada INMS-dentro-de-categoria tem um campo discriminador `mode`:

```yaml
categorias:
  ATENDIMENTO_N1:
    label: "Atendimento Remoto aos Usuários"
    inms:
      "1.1": {mode: grupo_executor, in_values: ["(CIT/MINC) - 1º Nível"]}
      "1.11": {mode: whole_indicator}
  OPERACAO_N3:
    label: "Operação e Sustentação da Infraestrutura de TI"
    inms:
      "1.1": {mode: grupo_executor, catch_all_contains: "(CIT)"}
      "1.9": {mode: whole_indicator}
  MONITORAMENTO_NOC_SOC:
    label: "Monitoramento de Ambiente (NOC/SOC)"
    inms:
      "1.4": {mode: whole_indicator}
      "1.14": {mode: whole_indicator}
```

- **`mode: grupo_executor`** com `in_values` (lista explícita, reaproveita o tipo `ColumnIn` já
  existente em `src/pyauditor/config/models.py`, usado hoje em `SegmentedCategory`) ou
  `catch_all_contains` (não é uma lista fechada —
  a exclusão dos grupos já reivindicados por outras categorias do mesmo INMS/órgão é **computada em
  tempo de execução por `split`**, não hardcoded no YAML).
- **`mode: whole_indicator`**: sem filtro — o dataset inteiro do INMS naquela competência conta
  como a categoria, sem passar por `split`. Cobre tanto indicadores pré-agregados sem a coluna
  `Grupo_executor` (o trio NOC/SOC — 1.4, 1.5, 1.14) quanto INMS que deveriam ter a coluna mas cujo
  CSV real não tem (1.11, 1.12, 1.13, 1.9, e 1.6 especificamente no MinC — no MTur 1.6 tem a coluna
  real e usa `grupo_executor` normalmente). Quando um INMS sem coluna pertenceria a várias
  categorias nominalmente, a regra é **não duplicar**: conta só na categoria de infraestrutura
  (`OPERACAO_N3`) — exceto 1.14, duplicado intencionalmente entre `MONITORAMENTO_NOC_SOC` e
  `OPERACAO_N3` (mesmo resultado pré-agregado rotulado sob as duas).
- `outros` e "INMS sem categoria" (1.8, 1.10) não têm entrada no arquivo — implícitos.

Mapeamento INMS↔categoria completo:

| Categoria | INMS |
|---|---|
| Atendimento Remoto aos Usuários (`ATENDIMENTO_N1`) | 1.1, 1.2, 1.6, 1.7, 1.11, 1.12, 1.13 |
| Atendimento Presencial aos Usuários (`ATENDIMENTO_N2`) | 1.1, 1.2, 1.6, 1.7, 1.9 |
| Operação e Sustentação da Infraestrutura de TI (`OPERACAO_N3`) | 1.1, 1.2, 1.3, 1.6, 1.7, 1.9, 1.14 |
| Monitoramento de Ambiente — NOC/SOC (`MONITORAMENTO_NOC_SOC`) | 1.4, 1.5, 1.14 |

1.8 e 1.10 não têm categoria — seus schemas de ingestão manual (§2.2, §11.3) são estruturalmente
incompatíveis com `Grupo_executor` (registros de ocorrência/checklist, não solicitações de
atendimento).

### 14.3 Etapa `split`

`measure` permanece 100% inalterado. `pyauditor split <competência>` é um quinto comando standalone
(mesmo padrão de `bootstrap`/`measure`/`report`/`consolidate`); em `run`, entra **entre `bootstrap`
e `measure`**, transacional por órgão como os demais.

Para cada par (INMS, categoria) em `mode: grupo_executor`, `split` gera:

- **CSV filtrado**: `input/<orgao>/<ano>/<mes>/_split/<inms>/<categoria>.csv`.
- **Config de indicador derivada**: `configs/<orgao>/inms-<n>.<categoria>.yaml` — copia
  `quality_gates`/`calculation`/`target`/`penalty` do `inms-<n>.yaml` base, muda só `id` e
  `source.csv` (nunca `source.dataset` — `split` não toca em `datasets.yaml`). O ponto extra no nome (`inms-<n>.<categoria>.yaml`, nunca
  presente no arquivo base) deixa a config gitignored e ainda assim descoberta automaticamente pelo
  glob não-recursivo já existente de `measure` — nenhuma mudança em `measure` é necessária. Ver ADR
  [0002](../adr/0002-config-por-categoria-gerada-pelo-split.md) para o porquê de gerar em vez de
  escrever à mão.

`outros` só gera o CSV filtrado (auditoria), sem config derivada — não entra no cálculo. `split`
sempre sobrescreve ao rerodar (idempotência por regeneração; o CSV bruto original nunca é tocado).
`catch_all_contains` é resolvido em tempo de `split`: lê os valores literais de `Grupo_executor`
realmente presentes no CSV bruto daquela competência/órgão, subtrai os já reivindicados por
`in_values` de outras categorias do mesmo INMS/órgão, e o resto vira o filtro efetivo.

INMS em `mode: whole_indicator` pulam `split` inteiramente — nem CSV filtrado, nem config derivada;
a medição da categoria é a medição do `inms-<n>.yaml` base direto.

**Log de `outros`**: sempre que uma categoria `outros` tiver linhas (literal de `Grupo_executor`
novo, não previsto em `categorias.yaml` — §14.1), `split` emite um `WARNING` (não um `INFO` de
contagem), pra não depender de alguém abrir o xlsx sintético pra notar:

```
WARNING: INMS 1.1 (MinC/2026-06), categoria outros: 3 linha(s) não classificada(s) em nenhuma categoria — revisar categorias.yaml
```

### 14.4 Relatório xlsx sintético

Um `sintetico.xlsx` por órgão/competência (proposto: `reports/<orgao>/<ano>/<mes>/`, geração proposta
para `split` — não contestado nesta rodada, revisar no ticket de implementação se necessário), uma
aba por INMS com entrada em `categorias.yaml` (exclui 1.8/1.10). Contagens são
**brutas, pré-quality-gate** — conferência rápida, não substitui o ROM oficial da categoria.

Colunas (uma linha por par categoria × valor de `Grupo_executor`, para INMS em `mode:
grupo_executor`): `Categoria` | `Nível` | `Grupo executor` | `Linhas` | `Dentro do prazo` | `Fora do
prazo` | `% bruto` | `Tempo médio criação→resolução` (de `DataHoraFim − DataHoraSolicitacao`, sobre
as linhas aprovadas pelo quality gate daquela linha). `Nível` deriva da categoria:
`ATENDIMENTO_N1`→N1, `ATENDIMENTO_N2`→N2, `OPERACAO_N3`→N3, `MONITORAMENTO_NOC_SOC`→N3; `outros`
não tem Nível. Abaixo da tabela, um bloco de subtotais por Nível (soma de `Linhas`/`Dentro do
prazo`/`Fora do prazo`, `% bruto` e tempo médio agregados).

INMS em `mode: whole_indicator`: linha única, `Grupo executor` = `"(indicador inteiro)"`, sem bloco
de subtotais (não há granularidade pra subtotalizar numa aba de uma linha só).

"Não ativado" (dataset ausente na competência, §14.1): linha única mesclada com a frase `"Esse
serviço não foi requisitado no período selecionado."` no lugar da tabela. No log do CLI, uma forma
telegráfica distinta (não a mesma frase em prosa) — públicos diferentes, operador no terminal vs.
leitor do relatório final —, emitida só por `measure` (é quem descobre a ausência; `split` não
duplica a mensagem, já que `run` executa os dois em sequência):

```
WARNING: INMS 1.8 (MinC/2026-06): não ativado — dataset ausente (serviço não requisitado no período)
```

### 14.5 Composição com multi-ativo (INMS 1.14)

Quando um INMS é medido tanto por Categoria quanto por Ativo (ver item "multi-ativo" na lista de fog
resolvido acima, e o termo `Ativo` em `CONTEXT.md`), a composição é **produto cartesiano por
ativo**: cada Ativo é medido sob cada Categoria à qual o INMS pertence. O único caso hoje é o INMS
1.14 — 2 categorias (`MONITORAMENTO_NOC_SOC`, `OPERACAO_N3`, ambas `whole_indicator`) × 6 ativos
nomeados no Anexo D (File Server, Telefonia, Mensageria, Servidores de impressão, WI-FI, Rede) = 12
medições independentes, cada uma seu próprio ROM. `whole_indicator` aqui significa apenas "sem
filtro de `Grupo_executor`" — não colapsa os ativos, que já são medições separadas por razão
distinta (definição do próprio Anexo D).

No xlsx sintético, a aba do INMS 1.14 troca a coluna `Grupo executor` por **`Ativo`** e mostra as 12
linhas agrupadas e subtotalizadas por categoria (bloco NOC/SOC, depois bloco Operação N3) — mesmo
padrão de linhas agrupadas com subtotal do §14.4, sem estrutura de aba nova.

Nenhum INMS com `Grupo_executor` real (1.1, 1.2, 1.3, 1.6, 1.7, 1.9) é multi-ativo hoje, e isso é
estrutural ao Anexo D: multi-ativo cobre monitoramento de infraestrutura nomeada (NOC/SOC), enquanto
`Grupo_executor` existe em indicadores de fila de atendimento/chamado — categorias de indicador
diferentes no próprio contrato. O caso geral (produto cartesiano com `Grupo_executor` real, `split`
rodando de fato por ativo) é **fora do escopo** deste addendum — se surgir no futuro, é uma extensão
do modelo, tratada como novo esforço.

### Fog remanescente, explicitamente fora do destino desta versão da spec

1. **Schema do dataset de origem/ingestão de ocorrências do INMS 1.8** (§11.3) e **de controles de
   segurança do INMS 1.10** (§2.2) — formato ITSM plausível mas não confirmado para nenhum dos dois.
   Ambos têm um schema de preenchimento manual provisório documentado e testado (§11.3, §2.2), mas
   isso não resolve a pergunta de qual sistema real, se algum, deveria alimentar esses dados —
   permanece uma pergunta em aberto para a equipe de fiscalização.
2. **Fórmula de consolidação MinC/MTur para os indicadores de disponibilidade por ativo** (1.4, 1.5,
   1.14) — `docs/spreadsheet.md` exige uma fórmula específica do Termo de Referência para esses 3,
   não a fórmula padrão; essa fórmula específica não foi localizada em nenhuma fonte primária lida
   (ver §10).

Nenhum destes dois itens bloqueia a implementação do escopo coberto por esta spec (mono-órgão,
1 CSV por indicador); cada um deve ser resolvido — com o gestor do contrato ou com novos dados
reais — antes de estender o pipeline além do escopo atual.

> **Atualização:** a convenção de descoberta de arquivos para múltiplos ativos/serviços por
> indicador (item 3 original desta lista) foi resolvida — `Indicator.asset` distingue medições que
> compartilham `contractual_id` (ex.: INMS 1.14 por serviço nomeado — File Server, WI-FI, etc.),
> `measure` grava um ROM/JSON por ativo sem colisão de nome, e `report` mostra uma linha por ativo em
> `INMS_BASE` e na aba de grupo, ordenada por `(contractual_id, asset)`. Provado com fixtures
> sintéticas (`tests/fixtures/multi_asset_configs/`) já que `/input` ainda não tem mais de 1 CSV por
> indicador. Convenção de nomenclatura de arquivo: `inms-<n>-<asset-slug>.yaml`.
