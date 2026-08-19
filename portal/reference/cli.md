# CLI — `pyauditor`

Referência da interface de linha de comando. Três subcomandos, pensados para
rodar em fases separadas (o fiscal pode re-rodar `measure` quando chegam novos
CSVs sem refazer o mês inteiro).

## Sintaxe

```text
pyauditor <subcomando> [argumentos]
```

Subcomandos: `bootstrap`, `measure <competência>`, `report <competência>`.
A competência usa o formato `YYYY-MM` (ex.: `2026-06`).

## `bootstrap`

Cria o Excel de capa do contrato se ele ainda não existir. **Idempotente** —
nunca recria um arquivo que já existe.

```text
pyauditor bootstrap [--capa-path PATH]
```

| Opção | Default | Descrição |
|---|---|---|
| `--capa-path` | `capa.xlsx` | Caminho da planilha de capa a criar |

Saída (stdout/log): `capa criada: <path>` ou `capa já existe, nada a fazer`.
Exit code 0 sempre que o caminho é gravável.

## `measure <competência>`

A pura cada indicador configurado para a competência e grava um ROM Markdown +
sumário JSON por indicador.

```text
pyauditor measure <competência> [--config-dir DIR] [--data-dir DIR] [--output-dir DIR] [--manifest PATH]
```

| Opção | Default | Descrição |
|---|---|---|
| `competência` | (obrigatório) | `YYYY-MM` |
| `--config-dir` | `configs/` | Diretório dos `inms-<n>.yaml` |
| `--data-dir` | `input/` | Raiz de dados; lê de `<data-dir>/<ano>/<mês>/` |
| `--output-dir` | `roms/` | Grava em `<output-dir>/<competência>/` |
| `--manifest` | `configs/datasets.yaml` | Manifesto de datasets (alias → arquivo) |

Saídas por indicador, em `<output-dir>/<competência>/`:

- `<sanitized-id>.md` — ROM Markdown (render via `rom/render.py`).
- `<sanitized-id>.json` — sumário estruturado (`IndicatorSummary`).

Comportamento de falha: erros de medição são logados e **não interrompem os
demais indicadores**; o exit code é 1 se houve alguma falha dura (`hard_failure`
ou exceção). Um CSV vazio de origem **não** é falha dura; um CSV cujas linhas
todas foram rejeitadas pelos quality gates é.

## `report <competência>`

Consolida os sumários de uma competência no Excel final. Lê os JSON de `roms`,
a capa (`capa.xlsx`) e (se disponíveis) os configs para abas `CADASTROS` e
`EVIDENCIAS`.

```text
pyauditor report <competência> [--capa-path PATH] [--roms-dir DIR] [--output-dir DIR] [--config-dir DIR]
```

| Opção | Default | Descrição |
|---|---|---|
| `competência` | (obrigatório) | `YYYY-MM` |
| `--capa-path` | `capa.xlsx` | Capa criada por `bootstrap` |
| `--roms-dir` | `roms/` | Lê de `<roms-dir>/<competência>/` |
| `--output-dir` | `reports/` | Grava `relatorio_<competência>.xlsx` |
| `--config-dir` | `configs/` | Usado para `CADASTROS`/`EVIDENCIAS` |

Pré-condições:
- a capa existe (`--capa-path`) — erro se não;
- `<roms-dir>/<competência>/` existe com `.json` (erro se vazio/ausente).

## Logs

Cada execução grava um log timestampado no diretório de saída do comando:
`pyauditor-<comando>[-<competência>]-<datahora>.log` (via
`pyauditor.logging.setup_logging`).

## Fontes primárias

- `src/pyauditor/cli/main.py` — parser/flags e defaults.
- `src/pyauditor/cli/{bootstrap,measure,report}.py`.