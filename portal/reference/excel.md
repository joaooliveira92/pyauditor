# Planilha Excel final

O `report` consolida a competência, por órgão, em um workbook
`relatorio_<competência>_<orgao>.xlsx`, montado em `src/pyauditor/excel/report.py`.
O `consolidate` funde os dois órgãos em um segundo workbook (ver
[Workbook consolidado](#workbook-consolidado) abaixo).
Referência estrutural: `docs/spreadsheet.md`; formatação: `docs/styleguide.md`.

## Abas

| Aba | Conteúdo | Fonte |
|---|---|---|
| `CAPA_E_CONTROLE` | Campos da capa preenchidos pelo fiscal (embedded da `capa_<orgao>.xlsx`) | `excel/capa.py` |
| `CADASTROS` | Código/descrição/formato/meta/penalidades por indicador | configs |
| `INMS_BASE` | Uma linha por `Competência + grupo + indicador + órgão` | sumários JSON |
| `ATENDIMENTO_N1` | Resultados por órgão da aba de atendimento remoto | sumários |
| `MONITORAMENTO_NOC_SOC` | Indicadores de disponibilidade por ativo (1.4, 1.5, 1.14) | sumários |
| `ATENDIMENTO_N2` | Atendimento presencial (grupo) | sumários |
| `OPERACAO_N3` | Operação e sustentação (grupo) | sumários |
| `GLOSAS` | Glosa monetária: soma de pontos, % de ajuste, valor, teto, rollover | `excel/glosas.py` |
| `EVIDENCIAS` | Controle de evidências por indicador (preenchimento manual) | configs + fiscal |

### Mapeamentos e regras

- **Grupo por indicador:** primeiro-match em `excel/groups.py`
  (`ATENDIMENTO_N1`, `MONITORAMENTO_NOC_SOC`, `ATENDIMENTO_N2`, `OPERACAO_N3`);
  indicadores fora das abas de grupo (ex.: INMS 1.8) têm grupo nulo.
- **Ordenação `INMS_BASE`:** por `(contractual_id, asset)`.
- **Consolidação MinC/MTur:** o `report` é por órgão — não mistura `MinC` e
  `MTur` no mesmo arquivo. A fusão entre os dois órgãos ocorre no workbook
  consolidado do `consolidate` (ver abaixo).
- **Glosa:** `Ajuste_NMS(%) = min(30%, Σ Pontos_NMS × 0,001%)`; valor = %
  × **Valor mensal vigente** (da capa). Teto de 30% com saldo rolado para o mês
  seguinte (exceto mês final). Sem `Valor mensal vigente` preenchido, a aba
  `GLOSAS` mostra o percentual mas sem valor (log avisa).
- **Abas vazias são evitadas** quando não há indicadores do grupo.

## Colunas `INMS_BASE`

`Competência, Item contratual, Serviço, Grupo operacional, Código INMS,
Descrição, Órgão, Meta mínima ou máxima, Sentido da meta, Numerador,
Denominador, Resultado calculado, Unidade, Aplicabilidade, Resultado esperado,
Conformidade, Diferença para a meta, Ocorrência de glosa, Percentual de glosa,
Valor-base, Valor da glosa, Justificativa, Referência da evidência, Número
SEI, Responsável pela evidência, Observação do fiscal`.

Colunas de preenchimento manual do fiscal ficam em branco (nada é fabricado).

## Workbook consolidado (`consolidate`)

O `consolidate` funde os relatórios `MinC` e `MTur` em
`relatorio_<competência>_consolidado.xlsx`, montado em
`src/pyauditor/excel/consolidate.py`. É idempotente nas colunas de decisão do
fiscal: ao re-executar sobre um consolidado já decorado, conserva `Reincidencia`,
`Justificativa`, `Número da Ocorrência`, `Decisão Fiscal` e `Observação do
Gestor` (nunca recalcula essas células). Abas:

| Aba | Conteúdo | Fonte |
|---|---|---|
| `CAPA_E_CONTROLE` | Campos da capa consolidados; `Valor mensal vigente` de `MinC` manda se diverge (aviso) | capas de ambos os órgãos |
| `SERVICOS_POR_ORGAO` | 9 serviços contratuais fixos e critério de rateio provisório (50/50) | `excel/consolidate.py` |
| `INMS_BASE` | Uma linha por `(item contratual, ativo, órgão)` + linha `"Consolidado"` | sumários JSON de ambos os órgãos |
| `GLOSAS` | Uma linha por `(indicador × órgão)` + resumo agregado e `Decisão Fiscal` | `excel/consolidate.py` |
| `CALCULO_PAGAMENTO` | Bruto, pontos de glosa, glosa e valor recomendado; colunas MinC/MTur/Consolidado | `excel/consolidate.py` |

- **Consolidação `INMS_BASE`:** para o mesmo indicador (mesmo `contractual_id`
  e `asset`) com medições de `MinC` e `MTur`, uma linha `"Consolidado"` com a
  fórmula ponderada `(Num MinC + Num MTur) / (Den MinC + Den MTur)` — exceto
  para os indicadores de disponibilidade por ativo (1.4, 1.5, 1.14), que nunca
  são consolidados (fórmula específica não localizada na spec). Ver
  `excel/orgao_consolidation.py` e spec §10.
- **Glosa:** totaliza os pontos dos dois órgãos e aplica o teto único de 30% ao
  agregado; a `Decisão Fiscal` "aceita" retira a ocorrência da base de pontos.

## Valor mensal vigente

`report` lê "Valor mensal vigente" da `capa_<orgao>.xlsx`
(`capa.read_valor_mensal_vigente`). Sem esse campo, a glosa sai sem valor.

## Fontes primárias

- `src/pyauditor/excel/report.py` — abas e colunas do `report` por órgão.
- `src/pyauditor/excel/consolidate.py` — workbook consolidado.
- `src/pyauditor/excel/{capa,glosas,groups,orgao_consolidation}.py`
- `docs/spreadsheet.md` — referência estrutural das abas.
- `docs/styleguide.md` — formatação.