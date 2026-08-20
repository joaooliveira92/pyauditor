# Quickstart — apure uma competência

Objetivo: rodar a cadeia completa `bootstrap` → `measure` → `report` →
`consolidate` para a competência `2026-06` (órgão `MinC`) e obter as planilhas
finais.

## Pré-requisitos

- Projeto instalado ([Instalação](installation.md)).
- Pastas `configs/MinC/` (configs dos indicadores) e `input/MinC/2026/06/`
  (CSVs da competência — **não versionados**, ver
  [layout de dados](../concepts/data-layout.md)).

## Procedimento

1. Crie a capa do órgão (idempotente — não sobrescreve se já existir):

   ```bash
   uv run pyauditor bootstrap --orgao MinC --capa-path capa_MinC.xlsx
   ```

   Saída esperada: `capa criada: capa_MinC.xlsx` (ou
   `capa já existe, nada a fazer`).

2. Preencha a capa no Excel (opcional para `measure`, necessário para a glosa
   monetária no `report`), gravando ao menos **Valor mensal vigente**.

3. Meça todos os indicadores da competência:

   ```bash
   uv run pyauditor measure 2026-06 --orgao MinC --config-dir configs --data-dir input --output-dir roms
   ```

   Saída esperada: um log por indicador como
   `INMS 1.1: roms/MinC/2026-06/INMS-1.1.md`.

4. Gere o relatório do órgão:

   ```bash
   uv run pyauditor report 2026-06 --orgao MinC --capa-path capa_MinC.xlsx --roms-dir roms --output-dir reports
   ```

   Saída esperada: `reports/relatorio_2026-06_MinC.xlsx` com as abas do órgão.

5. (Opcional) Gere o consolidado financeiro dos dois órgãos. Se os dois
   relatórios (`MinC` e `MTur`) já existem, rode o `consolidate`:

   ```bash
   uv run pyauditor consolidate 2026-06 --report-dir reports --roms-dir roms
   ```

   Ou, para rodar toda a cadeia dos dois órgãos de uma vez (`bootstrap` →
   `measure` → `report` → `consolidate`), use o `run`:

   ```bash
   uv run pyauditor run 2026-06 --orgao both --config-dir configs --data-dir input --output-dir roms --report-dir reports
   ```

   Saída: `reports/relatorio_2026-06_consolidado.xlsx`.

## Verificação

- `roms/MinC/2026-06/` contém um `.md` e um `.json` por indicador apurado.
- `reports/relatorio_2026-06_MinC.xlsx` abre no Excel com abas `CAPA_E_CONTROLE`,
  `CADASTROS`, `INMS_BASE`, abas por grupo, `GLOSAS` e `EVIDENCIAS`.
- `reports/relatorio_2026-06_consolidado.xlsx` abre com as abas
  `CAPA_E_CONTROLE`, `SERVICOS_POR_ORGAO`, `INMS_BASE`, `GLOSAS` e
  `CALCULO_PAGAMENTO`.

## Falhas comuns

### `competência inválida`

O argumento deve seguir o formato `YYYY-MM` (ex.: `2026-06`).

### `nenhuma capa encontrada` no report

Rode `bootstrap` antes de `report`, ou passe o caminho correto por órgão com
`--capa-path`.

### `nenhum sumário de medição (.json) encontrado`

`measure` não rodou para essa competência/órgão (ou os `.json` foram apagados).
Rode o passo 3 antes do passo 4.

### `consolidate` sem os dois relatórios

`relatorio_2026-06_MinC.xlsx` e `_MTur.xlsx` precisam existir antes do
`consolidate` (ele não re-executa `measure`/`report`).

Veja mais em [Troubleshooting](../operations/troubleshooting.md).

## Próximos passos

- [Leia o ROM e o JSON](../reference/rom.md) para interpretar cada medição.
- Entenda [como o pipeline funciona](../concepts/pipeline.md).