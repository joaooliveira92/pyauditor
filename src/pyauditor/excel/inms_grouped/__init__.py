"""Aba `INMS_BASE_AGRUPADO` do `relatorio_<competência>_consolidado.xlsx` —
uma visão do `INMS_BASE` da mesma aba com agrupamento nativo de linhas do
Excel (Dados > Agrupar). Todo Código INMS segue o mesmo formato pai/filho:
um `"Consolidado"` (total geral, nível 0) com `"Consolidado - MinC"`/
`"Consolidado - MTur"` (nível 1) como filhos — nunca um órgão pai do outro.
Substitui o pooling por Nível (N1/N2/N3) por um detalhamento real em dois
grupos de INMS:

- Por Grupo executor, nos INMS com essa granularidade em `categorias.yaml`
  (hoje: 1.1, 1.2, 1.3, 1.7 — descoberto em runtime via `_grupo_detail_by_
  inms`, não hardcoded).
- Por ativo/sistema, nos INMS "por ativo" listados em
  `_PRECOMPUTED_BREAKDOWN_CODES` (hoje: 1.4, 1.5, 1.9, 1.10, 1.13, 1.14 —
  todo `precomputed_table` com `numerator_column`/`denominator_column`/
  `name_column` configurados).

Por que não é fabricação:
- Grupo executor: cada linha de detalhe roda
  `SHAPE_REGISTRY[shape].calculate()` (o mesmo motor de `measure`) sobre o
  subconjunto de linhas aceitas (pós quality-gate) de um único
  Grupo_executor — somar essas linhas por categoria reproduz exatamente o
  numerador/denominador já publicado no `INMS_BASE` oficial (conferido
  manualmente).
- Por ativo: cada linha do dataset bruto já É o resultado computado de um
  ativo (`numerator_column`/`denominator_column` do `calculation.
  precomputed_table`); somar essas duas colunas reproduz a mesma aritmética
  que `PrecomputedTableStrategy.calculate` já faz internamente para o
  `result_pct` agregado por órgão (também conferido manualmente contra o
  ROM publicado) — só que exposta por ativo em vez de só o agregado.
- Verbatim reorganizado (`_restructure_verbatim`, os INMS sem nenhum dos
  dois detalhamentos): reusa a linha `"Consolidado"` já publicada no
  `INMS_BASE` quando existe (`with_orgao_consolidation`); quando não existe
  (ex. denominador 0 nos dois órgãos neste mês, ou shape nunca consolidado
  como `precomputed_table`), soma numerador/denominador dos dois órgãos
  quando ambos existem, ou o Resultado calculado direto quando o indicador
  é ponto/contagem sem numerador/denominador (ex. INMS 1.8) — nunca inventa
  uma razão que o indicador não tem.

"Consolidado - {órgão}" é sempre o subtotal/valor daquele órgão;
"Consolidado" é sempre a soma dos dois — aritmética direta sobre números já
corretos, nunca uma fórmula contratual nova.

Grupos executores fora de `categorias.yaml` ("Grupo sob análise de
responsabilidade") ficam de fora do detalhamento por grupo: `measure`/
`report` nunca os soma na apuração oficial, incluí-los aqui infllaria os
subtotais silenciosamente.

`add_inms_agrupado_sheet` é chamada por `cli/consolidate.py` logo depois de
`build_consolidated_workbook` montar o workbook em memória — lê o
`INMS_BASE` que acabou de ser escrito nele (nunca abre nada do disco) e
grava a aba nova ao lado. Se a recomputação falhar (configs/CSV brutos
ausentes, por exemplo num ambiente sem `input/`), `consolidate` degrada com
um aviso e publica o consolidado sem essa aba — nunca bloqueia o artefato
financeiro principal por causa dela.

O pacote é dividido por responsabilidade:
- `_types`: constantes e os dois dataclasses (`_CodeInfo`,
  `GroupedSheetResult`) compartilhados pelos demais módulos.
- `_detail`: recomputa o detalhamento por grupo executor/ativo direto de
  `config_dir`/`data_dir` (lê configs/CSV, roda o motor oficial).
- `_rows`: transforma esse detalhamento (ou o `INMS_BASE` já publicado) em
  linhas de planilha (`CellValue` por coluna).
- `_sheet`: escreve essas linhas no worksheet e aplica o agrupamento nativo
  do Excel — a única parte que fala com `openpyxl`.
- `_build`: orquestra os três acima nas duas entradas públicas.
"""

from __future__ import annotations

from typing import Final

from ._build import add_inms_agrupado_sheet, compute_glosa_item_detail
from ._types import GroupedSheetResult

__all__: Final[tuple[str, ...]] = (
    'GroupedSheetResult',
    'add_inms_agrupado_sheet',
    'compute_glosa_item_detail',
)
