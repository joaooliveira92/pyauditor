# Organização dos dados

O projeto guarda, lado a lado, configs versionados e dados de **produção fora
do git** (PII). Entender a divisão evita versionar dados sensíveis ou apagar
aferições passadas.

## Árvore de diretórios

```text
pyauditor/
├── configs/                 # versionado
│   ├── datasets.yaml        # manifesto: alias -> arquivo CSV + parsing
│   └── inms-<n>.yaml        # um config por indicador (opcional: por ativo)
├── input/                   # NÃO versionado (gitignore) — dados de produção
│   └── <ano>/<mês>/         # CSVs da competência (ex.: input/2026/06/)
├── roms/                    # NÃO versionado — saídas do measure (gerados)
│   └── <competência>/
│       ├── <id>.md          # ROM Markdown
│       └── <id>.json        # sumário estruturado
├── reports/                 # NÃO versionado — saídas do report (gerados)
│   └── relatorio_<competência>.xlsx
├── capa.xlsx                # NÃO versionado — criado por bootstrap
├── src/pyauditor/           # código do programa
├── tests/                   # testes + fixtures sintéticas (versionado)
└── docs/                    # documentação
```

## Entradas

- **Configs** (`configs/`): um `inms-<n>.yaml` por indicador (schema →
  quality gates → cálculo → meta/penalidade → teste de aceitação). Para
  indicadores por ativo, use `inms-<n>-<asset-slug>.yaml` (ex.: `inms-1.14-wifi.yaml`).
- **Manifesto** (`configs/datasets.yaml`): mapeia alias legíveis
  (ex.: `incidentes`) ao arquivo CSV + `delimiter` + `encoding`. Os configs
  referenciam pelo alias via `source.dataset`.
- **CSVs de produção**: em `input/<ano>/<mês>/` — **nunca na raiz de `input/`**.
  Cada `inms-<n>.csv` deve estar na competência que está sendo apurada.

## Saídas

- `roms/<competência>/<id>.md` — memória de cálculo legível.
- `roms/<competência>/<id>.json` — o `report` lê apenas estes.
- `reports/relatorio_<competência>.xlsx` — planilha final consolidada.

## Dados de produção vs fixtures

- Dados de produção ficam **fora do versionamento** (`input/` no `.gitignore`)
  porque os CSVs trazem nome/solicitante/criador/técnico (PII real).
- `tests/fixtures/` é always sintético/anonimizado, nunca cópia crua de um CSV
  de produção. Não copie dados reais para fixtures.

## Fontes primárias

- `.gitignore`
- `docs/spec/inms-pipeline.md` §8