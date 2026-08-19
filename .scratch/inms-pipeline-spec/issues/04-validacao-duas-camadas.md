Type: grilling
Status: resolved

## Question

Onde a validação de `quality_gates.error` falha a medição? Uma camada só, ou validação estrutural do YAML/config (Pydantic) separada da validação de dados (linha a linha do CSV, gerando o relatório de rejeitados do ROM)?

## Answer

Duas camadas separadas:
- **Pydantic** cuida do "isso é um YAML/config válido" (schema errado, coluna obrigatória ausente na declaração) — fail-fast, erro de programador/config, antes mesmo de ler o CSV.
- **`QualityGateRunner`** cuida do "esses dados batem com as regras de negócio declaradas" (`quality_gates.checks` do YAML) — fail de medição, roda depois do parse do CSV e antes do cálculo, produz os "rejeitados com ID e motivo" que alimentam o ROM.

Misturar as duas faria o ROM perder a distinção entre "config quebrada" e "dado rejeitado".
