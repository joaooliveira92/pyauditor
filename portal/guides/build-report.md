# Consolide o relatório Excel

Use este procedimento para transformar os sumários de uma competência no
workbook final. Rode depois do `measure` da mesma competência.

## Pré-requisitos

- Capa criada: `capa_<orgao>.xlsx` (use [Crie a capa do contrato](bootstrap-capa.md)).
- Medição feita: `roms/<orgao>/<competência>/` com os `.json` (use [Meça uma
  competência](measure-indicators.md)).

## Procedimento

1. Rode o relatório do órgão:

   ```bash
   uv run pyauditor report 2026-06 --orgao MinC --capa-path capa_MinC.xlsx --roms-dir roms --output-dir reports
   ```

2. Abra `reports/relatorio_2026-06_MinC.xlsx` para revisão.

3. (Opcional, quando os dois órgãos estão prontos) Funde os relatórios MinC+MTur
   no consolidado financeiro:

   ```bash
   uv run pyauditor consolidate 2026-06 --report-dir reports --roms-dir roms
   ```

   Exige que `relatorio_2026-06_MinC.xlsx` e `_MTur.xlsx` já existam (não
   re-executa `measure`/`report`). Saída:
   `reports/relatorio_2026-06_consolidado.xlsx`.

## Verificação

- O arquivo existe em `reports/relatorio_2026-06_<orgao>.xlsx` e o log mostra
  `relatório consolidado: <path> (N indicadores)`.
- As abas esperadas estão presentes — veja [Planilha Excel](../reference/excel.md).
- (consolidado) `reports/relatorio_2026-06_consolidado.xlsx` abre com as abas
  `CAPA_E_CONTROLE`, `SERVICOS_POR_ORGAO`, `INMS_BASE`, `GLOSAS` e
  `CALCULO_PAGAMENTO`.

## Falhas comuns

- **`capa não encontrada`** — rode `bootstrap` antes; confira `--capa-path`.
- **`nenhum ROM encontrado`** / **`nenhum sumário (.json)`** — rode `measure`
  para a competência primeiro (ou aponte `--roms-dir` certo).
- **Aviso de capa sem «Valor mensal vigente»** — a aba `GLOSAS` sai com
  percentual de ajuste mas sem valor; preencha o campo na capa e re-rode.

## Observações

- `CADASTROS` é preenchido a partir dos configs; se o `--config-dir` falhar ao
  carregar, as abas `CADASTROS`/`EVIDENCIAS` são omitidas com aviso (o restante
  do relatório é gerado).
- Para o **último mês de vigência** do contrato, o parâmetro de mês final é
  aplicado na glosa (não há rollover para mês seguinte) — ver
  `excel/glosas.py`.

## Próximos passos

- [Adicionar um indicador](add-indicator.md)