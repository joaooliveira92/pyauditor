# Planilha Excel final

O `report` consolida a competência em um workbook
`relatorio_<competência>.xlsx`, montado em `src/pyauditor/excel/report.py`.
Referência estrutural: `docs/spreadsheet.md`; formatação: `docs/styleguide.md`.

## Abas

| Aba | Conteúdo | Fonte |
|---|---|---|
| `CAPA_E_CONTROLE` | Campos da capa preenchidos pelo fiscal (embedded da `capa.xlsx`) | `excel/capa.py` |
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
- **Consolidação MinC/MTur:** quando o mesmo indicador (mesmo `contractual_id`
  e `asset`) tem medições de `MinC` e `MTur`, uma linha `"Consolidado"` é
  adicionada com a fórmula ponderada
  `(Num MinC + Num MTur) / (Den MinC + Den MTur)` — exceto para os
  indicadores de disponibilidade por ativo (1.4, 1.5, 1.14), que nunca são
  consolidados (fórmula específica não localizada na spec). Ver
  `excel/orgao_consolidation.py` e spec §10.
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

## Valor mensal vigente

`report` lê "Valor mensal vigente" da `capa.xlsx`
(`capa.read_valor_mensal_vigente`). Sem esse campo, a glosa sai sem valor.

## Fontes primárias

- `src/pyauditor/excel/report.py` — abas e colunas.
- `src/pyauditor/excel/{capa,glosas,groups,orgao_consolidation}.py`
- `docs/spreadsheet.md` — referência estrutural das abas.
- `docs/styleguide.md` — formatação.