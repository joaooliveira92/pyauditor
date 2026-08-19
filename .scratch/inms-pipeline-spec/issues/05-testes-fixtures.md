Type: grilling
Status: resolved
Blocked by: 03

## Question

Como fixar reprodução? O `acceptance_test` de cada YAML vira um teste de fumaça automático sobre os 14 indicadores? As 4 (agora 3, ver ticket 13) strategies divergentes precisam de fixtures dedicadas além dos CSVs reais de produção?

## Answer

Duas camadas de teste:
- **Smoke test parametrizado**: `pytest.mark.parametrize` sobre todos os `acceptance_test` encontrados nos 14 pares yaml+csv — garante que a spec bate com a realidade contratual.
- **Fixtures sintéticas unitárias por strategy**: cada strategy divergente (`segmented_ratio`, `count_difference`, `external_catalog_sum`) ganha testes com fixtures sintéticas pequenas (não os CSVs reais de produção) para cobrir casos de borda da lógica isolada do dado de produção — rápido, sem depender de CSVs de centenas de linhas.
