Type: research
Status: resolved
Blocked by: 02

## Question

O ticket 02 supôs, a partir só do texto do Anexo D, que INMS 1.4/1.5/1.14 (disponibilidade) precisariam de uma strategy `per_asset_ratio` que agrega eventos brutos por ativo/serviço dentro de um único CSV. Isso bate com o formato real dos dados de produção?

## Answer

Não. Inspecionados os CSVs reais (`inms-001-04.csv`, `inms-001-05.csv`, `inms-001-14.csv` em `/Users/joao/dev/pyauditor/input/`): cada um é um **único registro já pré-agregado** por uma ferramenta de monitoramento externa (`Descrição, Disponibilidade Esperada (%), Disponibilidade Realizada (%), Disponibilidade Realizada (Tempo), UpTime, Error Budget Permitido, Error Budget Consumido, Error Budget Restante`) — não eventos brutos por ativo.

Decisão: **um YAML+CSV = um ativo/serviço = uma medição independente.** "Por ativo" (Anexo D: "para cada um dos sistemas/serviços, utilizar a fórmula ao lado") significa, na prática, múltiplos pares YAML+CSV (um por ativo/serviço), cada um tratado como uma medição `ratio` normal — não uma agregação interna multi-ativo. A strategy `per_asset_ratio` é eliminada; vira uma variação de fonte da strategy `ratio` (`aggregation: "precomputed"` — o numerador/denominador já vêm prontos do dataset, em vez de contados/somados a partir de linhas).

Isso reduz o engine de 5 para **4 shapes**: `ratio` (com variações `count_distinct` | `sum` | `precomputed`), `segmented_ratio`, `count_difference`, `external_catalog_sum`.

Fog remanescente (ver mapa): convenção de descoberta de arquivos quando um indicador tiver múltiplos ativos pré-agregados no mesmo período (hoje só há 1 CSV por indicador em `/input`).
