Type: research
Status: resolved

## Question

O Termo de Referência (Anexo D, Tabela 28) define 14 indicadores INMS. Todos têm a mesma forma de cálculo do INMS 1.1 (razão numerador/denominador × 100, meta com operador de comparação, penalidade em degraus), ou existem formas estruturalmente diferentes que exigem decisão explícita de engine?

## Answer

Lido o Anexo D (`docs/termo_de_referencia/anexo_d_prazos.html`) na íntegra, Tabela 28. Classificação:

**Mesma forma do INMS 1.1** (razão simples × 100, meta + penalidade em degrau — só configuração, zero decisão nova de engine): INMS 1.1, 1.3 (razão de somas de dias, não contagem distinta — coberto por `aggregation: sum` no YAML), 1.6, 1.7, 1.9, 1.11 (meta é "≤", direção invertida — coberto por `target.operator`), 1.12, 1.13.

**Shapes estruturalmente divergentes, exigem decisão de engine:**
- **INMS 1.2** — razão segmentada por 3 categorias (prioridade Alta/Média/Baixa), cada uma com meta e taxa de penalidade próprias, penalidade final = soma das 3. Shape: `segmented_ratio`.
- **INMS 1.4, 1.5, 1.14** — disponibilidade por sistema/serviço, aparentemente calculada individualmente por ativo (Anexo D diz "para cada um dos sistemas/serviços, utilizar a fórmula ao lado... não ao somatório"). **Revisado no ticket 13** após ver os dados reais: os CSVs de produção são um único registro pré-agregado por indicador, não eventos por ativo — a strategy vira uma variação de `ratio`, não um shape `per_asset_ratio` próprio.
- **INMS 1.10** — não é razão: `CNI = QRC − QCSI` (diferença de contagem), penalidade fixa por unidade faltante (não por degrau percentual). Shape: `count_difference`.
- **INMS 1.8** — somatório de pontos de um catálogo externo (Anexo E, fora do Anexo D), sem meta percentual. Shape: `external_catalog_sum`. Estrutura exata pendente — ver ticket 11 (research).

Resultado após revisão do ticket 13: o engine precisa de **4 shapes** (`ratio`, `segmented_ratio`, `count_difference`, `external_catalog_sum`), não 5.
