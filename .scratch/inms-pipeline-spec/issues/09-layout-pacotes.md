Type: grilling
Status: resolved
Blocked by: 03, 06

## Question

Qual o layout de pacotes concreto do repositório? Onde fica o registry de strategies — dict módulo-level ou entry_points/plugin discovery?

## Answer

```
src/pyauditor/
├── config/        # modelos Pydantic, discriminated union por `shape`
├── engine/
│   ├── quality_gates.py   # QualityGateRunner
│   └── strategies/         # ratio, segmented_ratio, count_difference, external_catalog_sum (ver ticket 13)
├── rom/            # renderização Markdown (template genérico + renderer por shape)
├── excel/          # builder da planilha final + capa (usa docs/spreadsheet.md e docs/styleguide.md)
└── cli/            # bootstrap / measure / report (+ comando guarda-chuva)
```

Registry de strategies: **dict módulo-level** (`SHAPE_REGISTRY: dict[str, type[CalculationStrategy]]` em `engine/strategies/__init__.py`), populado por import explícito de cada strategy — sem `entry_points`/plugin discovery, já que é mono-repo e as strategies são fixas e conhecidas (nunca vêm de fora do repo).
