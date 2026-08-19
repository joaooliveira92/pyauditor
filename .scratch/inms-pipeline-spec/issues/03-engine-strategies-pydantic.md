Type: grilling
Status: resolved
Blocked by: 02

## Question

Um único engine genérico parametrizado por config, versus código gerado por indicador? Para os shapes divergentes (ver ticket 02), isso vira estratégias plugáveis (strategy pattern) ou hard-code de casos especiais fora do engine comum? Que nível de tipagem Pydantic é usado para o YAML — um modelo único genérico, ou um schema por shape?

## Answer

- **Estratégias plugáveis via campo `shape` explícito no YAML** (registry/strategy pattern): mantém os 14 indicadores num único fluxo de execução (load config → valida quality_gates → aplica strategy → gera ROM). Evita "N pipelines paralelos" e deixa claro, olhando o YAML, qual forma de cálculo está em uso.
- **Pydantic com discriminated union pelo campo `shape`**: cada estratégia (`ratio`, `segmented_ratio`, `count_difference`, `external_catalog_sum` — ver ticket 13 para a revisão que eliminou `per_asset_ratio`) declara seu próprio modelo Pydantic para os blocos `calculation`/`penalty`, com `mypy --strict` garantindo que cada strategy só recebe o shape de config que sabe processar. Elimina `dict[str, Any]` e `# type: ignore` espalhados pelo engine.
