# pyauditor

Pipeline de aferição dos indicadores INMS (SLA) do **contrato 40/2022**, medidos
mensualmente por cada órgão contratante — **MinC** (Ministério da Cultura) e
**MTur** (Ministério do Turismo) — conforme o Anexo D (Prazos e Níveis Mínimos de
Servício) do Termo de Referência.

A partir de pares declarativos `inms-<n>.yaml` (config/schema) + `inms-<n>.csv`
(dataset) por indicador e órgão, `pyauditor`:

1. executa os **14 indicadores** do contrato (INMS 1.1–1.14) através de **quality
   gates** que podem rejeitar linhas do dataset;
2. escreve uma **memória de cálculo** (ROM) Markdown por indicador;
3. consolida tudo em um **Excel de relatório** por órgão mais uma **capa do
   contrato** (cover sheet);
4. **consolida** ambos os órgãos em um workbook financeiro único (glosa, cálculo
   de pagamento).

O resultado é uma aferição reproduzível, auditable e scriptable de cada
competência mensal do contrato.

Especificação completa: [`docs/spec/inms-pipeline.md`](docs/spec/inms-pipeline.md).
Documentação publicada: <https://joaooliveira92.github.io/pyauditor/>.

---

## Funcionalidades

- **4 shapes de indicador** reduzem o engine a um único fluxo de execução
  (`load config → valida quality_gates → aplica strategy → gera ROM`):
  `ratio`, `segmented_ratio`, `count_difference` e `external_catalog_sum`.
- **Strategy/registry pattern**: cada `shape` declara o seu próprio modelo
  Pydantic (discriminated union) — `mypy --strict` garante que cada strategy só
  recebe o config que sabe processar, sem `dict[str, Any]`.
- **Validação em duas camadas**: Pydantic (config é válida?) vs
  `QualityGateRunner` (os dados batem coas regras de negocio?). O ROM distingue
  "config quebrada" de "dato rejeitado".
- **Multi-órgao** (`MinC`/`MTur`/`both`): cada órgão roda isolado, sem cruzar
  dados; `consolidate` fusional-os só ao final.
- **Multi-activo por indicador** (`Indicator.asset`): um CSV por ativo/servicio
  (ex. INMS 1.14 File Server, WI-FI), sem colisão de nome.
- **Glosa fiscal** (`GLOSAS`): fórmula linear contínua do item 35 do TR
  (`min(30%, Σ Pontos × 0,001%) × valor mensual`) com teto e rollover.
- **Idempotencia e resume**: `bootstrap` nunca recria uma capa existente; `run`
  retoma onde ficou grazas ao estado em `.pyauditor/runs/`.

---

## Instalación

Requere **Python 3.12+** e [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

Isto instala o paquete e os grupos de dependências definidos em `pyproject.toml`
(`test`, `quality`, `security`, `docs`).

---

## Uso

### Fluxo interactivo

Executa `pyauditor` sem argumentos para um fluxo guiado que percorre toda a
competência (bootstrap → measure → report → consolidate), mostra progreso ao
vivo e oferece reintentar/omitir/abortar ante fallos. Requere um terminal real;
a entrada por pipe/non-interactiva cae nun erro que indica usar um subcomando
directamente.

### Subcomandos

Sepáranse em passos para que o fiscal técnico poida re-executar `measure`
conforme chegan novos CSVs sem refazer o mes completo, mais un `run` que encadea
todos nunha invocación scriptable:

| Comando | Responsabilidade |
|---|---|
| `bootstrap` | crea a capa Excel do contrato; **idempotente** |
| `measure <comp>` | apura os indicadores da competencia, xenera un ROM por indicador |
| `report <comp>` | consolida os ROMs no Excel de relatório do órgão |
| `consolidate <comp>` | funde os relatório MinC+MTur no workbook financeiro |
| `run <comp>` | encadea `bootstrap→measure→report→consolidate` |

`bootstrap`, `measure` e `report` aceitam `--orgao {MinC,MTur,both}` (default
`MinC`). Configs por órgão em `configs/<órgano>/`, dados em
`input/<órgano>/<AAAA>/<MM>`, ROMs em `roms/<órgano>/<competência>/`, e cada
órgano obtiene o seu próprio capa (`capa_<órgão>.xlsx`) e relatório
(`reports/relatorio_<competencia>_<orgao>.xlsx`).

```bash
# create each órgão's contract cover sheet (idempotent — skips existing files)
uv run pyauditor bootstrap --orgao both

# measure every configured indicator for a competência, per órgão
uv run pyauditor measure 2026-06 --orgao both --config-dir configs --data-dir input --output-dir roms

# consolidate each órgão's ROMs into its own Excel report
uv run pyauditor report 2026-06 --orgao both --roms-dir roms --output-dir reports

# fuse both órgãos' reports into the contract's financial workbook
uv run pyauditor consolidate 2026-06 --report-dir reports --roms-dir roms

# or, equivalently, chain all four steps in one non-interactive invocation
uv run pyauditor run 2026-06 --orgao both
```

`run` aceita os mesmos flags que os subcomandos individuais (`--config-dir`,
`--data-dir`, `--output-dir`, `--capa-path`, `--final-month`) e omite qualquer
passo xa `done` dunha invocación previa — o progreso é gardado por
`(competência, órgão)` em `.pyauditor/runs/`.

### Particularidades

- `measure` escrebe um `<indicator.id>.md` (ROM) e um `<indicator.id>.json`
  (resumen) por indicador; `report` le os resumos JSON, não o Markdown.
- `consolidate` **nunca re-executa** `measure`/`report`: requiere que existam os
  relatório de ambos os órgãos (erro no que falte) e escribe
  `reports/relatorio_<competencia>_consolidado.xlsx` (abas `CAPA_E_CONTROLE`,
  `SERVICOS_POR_ORGAO`, `INMS_BASE`, `GLOSAS`, `CALCULO_PAGAMENTO`). Re-executar
  sobre un consolidado xa decorado conserva as colunas de decisión fiscal
  (Justificativa / Decisión Fiscal / Observación) por `(indicador, órgão)`,
  actualizando só os campos recalcurados.
- `--final-month` no `report`/`run` desactiva o **rollover de glosa** (último
  mes de vigência do contrato, item 35 do TR).

---

## Como funciona: os 14 indicadores em 4 shapes

Leitura integral do Anexo D (Tabela 28) reduz o engine a catro shapes:

| Shape | Indicadores | Descrición |
|---|---|---|
| `ratio` | 1.1, 1.3–1.7, 1.9, 1.11–1.14 | numerador/denominador × 100, meta con operador (`>=`/`<=`), penalidade em degraus lineais |
| `segmented_ratio` | 1.2 | 3 sub-razóns por categoría (Alta/Media/Baixa), cada unha con meta e taxa propias; penalidade = suma |
| `count_difference` | 1.10 | `CNI = QRC − QCSI` (diferenza de contaxe), penalidade fixa por unidade |
| `external_catalog_sum` | 1.8 | suma de puntos dun catálogo externo pechado (Anexo E), sen meta percentual |

Variaciones de `ratio`: `count_distinct` (1.1, 1.6, 1.7, 1.9, 1.11–1.13), `sum`
(1.3), `precomputed` (1.4, 1.5, 1.14 — un YAML+CSV = un ativo/servicio = una
medición independente). Detalle e justificación contractual en
[`docs/spec/inms-pipeline.md`](docs/spec/inms-pipeline.md#2-classificación-dos-14-indicadores-por-shape).

---

## Estrutura do repositorio

```
src/pyauditor/
├── config/        # modelos Pydantic, discriminated union por `shape`, catálogo Anexo E
├── engine/
│   ├── quality_gates.py   # QualityGateRunner
│   └── strategies/        # ratio, segmented_ratio, count_difference, external_catalog_sum
├── rom/           # render Markdown (template genérico + renderer por shape)
├── excel/         # builder da planilla final + capa + glosas + consolidación
├── orchestration/ # estado do `run`, summary, execución encadeada
├── interactive/   # fluxo guiado (TTY)
└── cli/           # bootstrap / measure / report / consolidate / run

org/<órgao>/             # inms-<n>.yaml + datasets.yaml, por órgão
input/<órgao>/<AAAA>/<MM>    # datasets CSV (git-ignored; contén PII real)
roms/<órgao>/<competência>/  # ROMs .md + resumos .json
reports/                 # Excel de relatório por órgão + consolidado
docs/                    # spec, ADR, spreadsheet, styleguide, termo de referencia
portal/                  # fonte do site de documentación (zensical)
```

> Os dados de producción estão **fóra do versionado** (`input/`, git-ignored):
> os 14 CSVs levam nome/solicitante/criador/técnico (PII real). As fixtures de
> prueba em `tests/fixtures/` son sempre sintéticas ou anonimizadas.

---

## Desenvolvemento

```bash
uv run pytest          # suite completa + cobertura (>85%)
uv run mypy            # strict mode sobre src e tests
uv run ruff check src tests
uv run bandit src      # segurança
uv run pip-audit       # auditoría de dependencias
```

`mypy` roda em **strict mode** sobre `src` e `tests` (ver `pyproject.toml`). A
suite pytest está configurada con `pytest-cov` (branch coverage, limiar 85%),
`hypothesis` para tests baseados en propriedades, e fixtures sintéticas por
strategy — nunca cópia crúa de CSV de producción.

### Tests destacados

- **Smoke test parametrizado** sobre todos os `acceptance_test` dos 14 pares
  yaml+csv de producción — garante que a spec bate coa realidade contractual.
- Fixtures sintéticas unitarias por strategy diverxente (`segmented_ratio`,
  `count_difference`, `external_catalog_sum`) cobrindo casos de borde.
- Multi-órgao e multi-activo provados con fixtures sintéticas
  (`tests/test_orgao_consolidation.py`, `tests/fixtures/multi_asset_configs/`).

---

## Documentación

- **Spec**: [`docs/spec/inms-pipeline.md`](docs/spec/inms-pipeline.md) —
  arquitectura, decisións de deseño e remanescentes.
- **Glosario de dominio**: [`CONTEXT.md`](CONTEXT.md) — órgano, competencia,
  glosa, ROM, anistía, decisión fiscal, etc.
- **Estrutura das planillas**: [`docs/spreadsheet.md`](docs/spreadsheet.md) e
  [`docs/styleguide.md`](docs/styleguide.md).
- **Xit de decisións**: [`docs/adr/`](docs/adr/).
- **Site de documentación** (xerado com
  [zensical](https://docs.astral.sh/zensical/)): `uv run zensical build --clean`.

## Licencia e autor

Autor: Joao Antonio Oliveira (`joao.oliveira@cultura.gov.br`).