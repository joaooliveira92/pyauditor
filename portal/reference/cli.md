# CLI — `pyauditor`

Referência da interface de linha de comando. Os subcomandos estão pensados
para rodar em fases separadas: o fiscal pode rodar de novo `measure` quando
chegam novos CSVs, sem refazer o mês inteiro.

## Sintaxe

```text
pyauditor <subcomando> [argumentos]
```

Subcomandos: `bootstrap`, `measure <competência>`, `report <competência>`,
`consolidate <competência>`, `run <competência>`. A competência usa o formato
`YYYY-MM` (ex.: `2026-06`).

Sem argumentos, e com terminal interativo, `pyauditor` abre um **fluxo guiado**
que pede competência, órgão e pastas, e encadeia as etapas (ver
[Fluxo guiado](#fluxo-guiado) abaixo).

Todos os subcomandos (exceto `consolidate`) aceitam `--orgao MinC|MTur|both`
(default `MinC`). `both` roda o passo para os dois órgãos em sequência, sem
cruzar dados entre eles. A organização por órgão se reflete nas pastas
`configs/<orgao>/`, `input/<orgao>/`, `roms/<orgao>/` e nas capas
`capa_<orgao>.xlsx` (ver [Organização dos dados](../concepts/data-layout.md)).

## `bootstrap`

Cria o Excel de capa do contrato se ainda não existe. **Idempotente** — nunca
recria um arquivo que já existe.

```text
pyauditor bootstrap [--orgao MinC] [--capa-path PATH]
```

| Opção | Default | Descrição |
|---|---|---|
| `--orgao` | `MinC` | `MinC`, `MTur` ou `both`. Com `both` cria ambas capas |
| `--capa-path` | `capa_<orgao>.xlsx` | Caminho da planilha de capa a criar. O default por órgão só se usa quando `--orgao` não é `both` |

Saída: `capa criada: <path>` ou `capa já existe, nada a fazer`. Exit code 0
sempre que o caminho é gravável.

## `measure <competência>`

Apura cada indicador configurado para a competência e grava um ROM Markdown +
sumário JSON por indicador.

```text
pyauditor measure <competência> [--orgao MinC] [--config-dir DIR] [--data-dir DIR] [--output-dir DIR] [--manifest PATH] [--capa-path PATH]
```

### Opções

| Opção | Default | Descrição |
|---|---|---|
| `competência` | (obrigatório) | `YYYY-MM` |
| `--orgao` | `MinC` | `MinC`, `MTur` ou `both` |
| `--config-dir` | `configs/` | Lê os configs de `<config-dir>/<orgao>/` |
| `--data-dir` | `input/` | Raiz de dados; lê de `<data-dir>/<orgao>/<ano>/<mes>/` |
| `--output-dir` | `roms/` | Grava em `<output-dir>/<orgao>/<competência>/` |
| `--manifest` | `<config-dir>/<orgao>/datasets.yaml` | Manifesto de datasets (alias → arquivo) |
| `--capa-path` | `capa_<orgao>.xlsx` | Capa para os campos de Identificação/Responsáveis do ROM |

Saídas por indicador, em `<output-dir>/<orgao>/<competencia>/`:

- `<sanitized-id>.md` — ROM (render via `rom/render.py`).
- `<sanitized-id>.json` — sumário estruturado (`IndicatorSummary`).

Comportamento de falha: os erros de medição são logados e **não interrompem os
demais indicadores**; o exit code é `1` se houve alguma falha dura
(`hard_failure` ou erro inesperado). Um CSV vazio de origem **não** é falha
dura; um CSV cujas linhas foram todas rejeitadas pelos quality gates é.

## `report <competência>`

Consolida os sumários de uma competência no Excel final por órgão. Lê os JSON
de `roms/<orgao>/`, a capa (`capa_<orgao>.xlsx`) e (se houver) os configs
para as abas `CADASTROS` e `EVIDENCIAS`.

### Opções

| Opção | Default | Descrição |
|---|---|---|
| `competência` | (obrigatório) | `YYYY-MM` |
| `--orgao` | `MinC` | `MinC`, `MTur` ou `both` |
| `--capa-path` | `capa_<orgao>.xlsx` | Capa criada por `bootstrap` |
| `--roms-dir` | `roms/` | Lê de `<roms-dir>/<orgao>/<competencia>/` |
| `--output-dir` | `reports/` | Grava `relatorio_<competencia>_<orgao>.xlsx` |
| `--config-dir` | `configs/` | Usado para `CADASTROS`/`EVIDENCIAS` |
| `--final-month` | off | Último mês de vigência do contrato — desativa o rollover de glosa (item 35 do TR) |

### Pré-condições

- a capa existe (`--capa-path`) — erro se não;
- `<roms-dir>/<orgao>/<competencia>/` existe com `.json` (erro se vazio/ausente).

O `report` também grava `glosa_historico.json` junto aos ROMs do órgão
(`<roms-dir>/<orgao>/glosa_historico.json`) para o rollover e a reincidencia.

## `consolidate <competencia>`

Funde os sumários de MinC+MTur já gerados na planilha consolidada. **Não**
re-executa `measure`/`report`; requer que
`reports/relatorio_<competencia>_MinC.xlsx` e `_MTur.xlsx` já existam.

### Opções

| Opção | Default | Descrição |
|---|---|---|
| `competencia` | **obrigatório** | `YYYY-MM` |
| `--report-dir` | `reports/` | Lê os dois `relatorio_<comp>_<orgao>.xlsx` e grava o consolidado |
| `--roms-dir` | `roms/` | Sumários por órgão em `<roms-dir>/<orgao>/<competencia>/` |

Saída: `reports/relatorio_<competencia>_consolidado.xlsx` com as abas
`CAPA_E_CONTROLE`, `SERVICOS_POR_ORGAO`, `INMS_BASE`, `GLOSAS` e
`CALCULO_PAGAMENTO` (ver [Planilha Excel final](excel.md)). É idempotente nas
colunas de decisão do fiscal: ao re-executar sobre um consolidado já decorado,
conserva `Reincidencia`/`Justificativa`/`Número da Ocorrência`/
`Decisão Fiscal`/`Observação do Gestor`.

## `run <competencia>`

Encadeia `bootstrap` → `measure` → `report` → `consolidate` numa única invocação
scriptable (fases em ordem, por órgão; `consolidate` só quando `--orgao both`).

### Opções

| Opção | Default | Descrição |
|---|---|---|
| `competencia` | (obrigatório) | `YYYY-MM` |
| `--orgao` | `MinC` | `MinC`, `MTur` ou `both` |
| `--config-dir` | `configs/` | Raiz dos configs (por órgão) |
| `--data-dir` | `input/` | Raiz dos dados (por órgão) |
| `--output-dir` | `roms/` | ROMs (por órgão) |
| `--report-dir` | `reports/` | Relatórios e consolidado |
| `--capa-path` | `capa_<orgao>.xlsx` | Capa |
| `--final-month` | off | Último mês de vigência — desativa o rollover de glosa |

Saída: um resumo por etapa em stdout; exit code `1` se alguma etapa falha.
Retoma execuções interrompidas e conserva o estado em `.pyauditor/runs/`.

## Fluxo guiado

Com terminal interativo e sem subcomando, `pyauditor` abre o fluxo guiado: pede
competência, órgão e pastas, permite escolher quais etapas rodar e responder às
falhas (reintentar/omitir/abortar). Digitando `?` em qualquer pergunta mostra
ajuda contextual; `Ctrl+C` conserva o que já foi preenchido para retomar na
próxima execução. Implementado em `src/pyauditor/interactive/flow.py`.

## Logs

Cada execução grava um log com timestamp no diretório de saída do comando:
`pyauditor-<comando>[-<competencia>]-<datahora>.log` (via
`pyauditor.logging.setup_logging`).

## Fontes primárias

- `src/pyauditor/cli/main.py` — parser, flags e defaults.
- `src/pyauditor/cli/{bootstrap,measure,report,consolidate,run}.py`.
- `src/pyauditor/interactive/flow.py` — fluxo guiado.
- `src/pyauditor/orchestration/run.py` — `run` e a orquestração.