# Quickstart — apure uma competência

Objetivo: rodar a cadeia completa `bootstrap` → `measure` → `report` para a
competência `2026-06` e obter a planilha final.

## Pré-requisitos

- Projeto instalado ([Instalação](installation.md)).
- Pastas `configs/` (configs dos indicadores) e `input/2026/06/` (CSVs da
  competência — **não versionados**, ver [layout de dados](../concepts/data-layout.md)).

## Procedimento

1. Crie a capa do contrato (idempotente — não sobrescreve se já existir):

   ```bash
   uv run pyauditor bootstrap --capa-path capa.xlsx
   ```

   Saída esperada: `capa criada: capa.xlsx` (ou `capa já existe, nada a fazer`).

2. Preencha a capa no Excel (opcional para `measure`, necessário para a glosa
   monetária no `report`), gravando ao menos **Valor mensal vigente**.

3. Meça todos os indicadores da competência:

   ```bash
   uv run pyauditor measure 2026-06 --config-dir configs --data-dir input --output-dir roms
   ```

   Saída esperada: um log por indicador como `INMS 1.1: roms/2026-06/INMS-1.1.md`.

4. Consolide o relatório final:

   ```bash
   uv run pyauditor report 2026-06 --capa-path capa.xlsx --roms-dir roms --output-dir reports
   ```

   Saída esperada: `reports/relatorio_2026-06.xlsx` com as abas consolidadas.

## Verificação

- `roms/2026-06/` contém um `.md` e um `.json` por indicador apurado.
- `reports/relatorio_2026-06.xlsx` abre no Excel com abas `CAPA_E_CONTROLE`,
  `CADASTROS`, `INMS_BASE`, abas por grupo, `GLOSAS` e `EVIDENCIAS`.

## Falhas comuns

### `competência inválida`

O argumento deve seguir o formato `YYYY-MM` (ex.: `2026-06`).

### `nenhuma capa encontrada` no report

Rode `bootstrap` antes de `report`, ou passe o caminho correto com
`--capa-path`.

### `nenhum sumário de medição (.json) encontrado`

`measure` não rodou para essa competência (ou os `.json` foram apagados).
Rode o passo 3 antes do passo 4.

Veja mais em [Troubleshooting](../operations/troubleshooting.md).

## Próximos passos

- [Leia o ROM e o JSON](../reference/rom.md) para interpretar cada medição.
- Entenda [como o pipeline funciona](../concepts/pipeline.md).