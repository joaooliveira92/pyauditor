Type: grilling
Status: resolved

## Question

O código assume um único contrato governando os 14 indicadores, ou precisa de abstração para múltiplos contratos desde já? Onde vivem os YAML+CSV de produção (alguns têm `classification: personal_data`) vs as fixtures de teste?

## Answer

- **Mono-contrato, sem abstração prematura**: `scope.contract` já vem como valor fixo no YAML; "múltiplos contratos" seria só "múltiplos diretórios de config" no futuro — não exige decisão de arquitetura hoje.
- **Dados de produção fora do versionamento** (diretório configurável, git-ignorado — hoje em `/Users/joao/dev/pyauditor/input/`): os CSVs têm nome/solicitante/criador/técnico (PII real), então versioná-los arrisca vazar dados pessoais no histórico do git.
- **Fixtures de teste ficam no repo** (`tests/fixtures/`) mas devem ser sintéticas ou anonimizadas — nunca uma cópia crua do CSV de produção.
