# Meça uma competência

Use este procedimento para apurar os indicadores de um mês depois que os CSVs
da competência chegarem.

## Pré-requisitos

- Configs em `configs/` (e manifesto `datasets.yaml`).
- CSVs da competência em `input/<ano>/<mês>/`.

## Procedimento

1. Confira a estrutura de pastas:

   ```text
   configs/inms-1.1.yaml ...
   input/2026/06/inms-01.csv ...   (ou os nomes do datasets.yaml)
   ```

2. Rode a medição:

   ```bash
   uv run pyauditor measure 2026-06 --config-dir configs --data-dir input --output-dir roms
   ```

   Para usar um manifesto/CSVs fora dos defaults, ajuste `--config-dir`,
   `--data-dir`, `--output-dir` e `--manifest`.

## Verificação

- `roms/2026-06/` contém um par `<id>.md` + `<id>.json` por indicador.
- O log mostra `INMS x.y: <path>.md` por indicador aceito.
- Exit code `0` se não houve `hard_failure`; `1` se algum indicador falhou
  (o processamento continua para os demais).

## Falhas comuns

- **`competência inválida`** — use `YYYY-MM`.
- **`nenhum config encontrado`** — o `--config-dir` não tem `inms-*.yaml`.
- **`source.dataset=... requires a manifest`** — falta `configs/datasets.yaml`
  (ou `--manifest` apontando para ele).
- **`hard_failure` de um indicador** — todas as linhas existentes foram
  rejeitadas pelos quality gates; consulte o ROM gerado para os motivos. Um CSV
  vazio **não** gera falha dura (competência legítima sem lançamento).

## Próximos passos

- [Consolidar o relatório](build-report.md)
- [Ler o ROM e o JSON](../reference/rom.md)