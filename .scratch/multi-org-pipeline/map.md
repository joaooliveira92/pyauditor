# Map: pipeline multi-órgão (MinC/MTur)

Label: wayfinder:map

## Destination

Pipeline multi-órgão: `measure`/`report` por órgão (`MinC`, `MTur`, `both`), com dados em `input/<órgão>/<AAAA>/<MM>` e saídas com namespace por órgão, mais um subcomando `consolidate` (2.1) que lê **apenas** os relatórios por órgão já gerados (`reports/relatorio_<comp>_<orgao>.xlsx`) e produz a planilha financeira consolidada (núcleo: `CAPA_E_CONTROLE`, `INMS_BASE` consolidado, `GLOSAS`, `CALCULO_PAGAMENTO`, `SERVICOS_POR_ORGAO`) — sem refazer a etapa 1.3, para não sobrescrever edições do usuário.

## Notes

- Domínio: pyauditor — contrato 40/2022, indicadores INMS 1.1–1.14, órgãos MinC/MTur, competência `YYYY-MM`. Linguagem dos artefatos: português.
- Skills que toda sessão deve consultar: `grilling` e `domain-modeling` (default quando em dúvida); `prototype` para o ticket do mock; `research` para o ticket de inspeção da planilha de inspiração.
- Fatores já estabelecidos (não rediscutir): input já reorganizado em `input/MinC|MTur/2026/06/inms-*.csv`; MTur hoje com placeholders sintéticos; `orgao_consolidation.py` é o pooling MinC+MTur dentro do `report` que o `consolidate` vai substituir (resolver o ticket 07 do framework-audit).
- O fluxo 1.1/1.2/1.3 (measure+report por órgão) é `--orgao {MinC,MTur,both}`. A etapa 2.1 (`consolidate`) é **sempre** leitura; nunca invoca measure/report.
- Plan, don't do: este mapa resolve decisões; execução de implementação fica para depois que o caminho estiver claro (handoff).

## Decisions so far

- [Mapear as abas financeiras da planilha de inspiração](issues/01-inspiration-financial-tabs.md) — núcleo financeiro: `CAPA_E_CONTROLE` (valor mensal) → `GLOSAS` (Valor Glosa = Valor Base × %Ajuste/100; glosa final = MIN(pontos×0.001, 30%)×mensal) → `CALCULO_PAGAMENTO` (rateio MinC/MTur); **pontos de glosa são entrada manual no workbook** (cadeia indicador→pontos→glosa não automatizada).
- [Fórmula financeira da consolidação (2.1)](issues/02-consolidation-formula.md) — `GLOSAS` por (indicador×órgão) + resumo; pontos derivados (Σ %Ajuste×1000, sem D14 manual); teto único 30% no agregado; `CALCULO_PAGAMENTO` espelha a inspiração (rateio fiscal 0.5/0.5, glosa na coluna consolidada); `INMS_BASE` = pooling atual movido para o consolidate; **sugestão de glosa**: fiscal aceita/não-aceita justificativa (anistia), decisões na planilha, re-rodada preserva células editadas (merge).

Decisões de fundação aprovadas no grill (Q1–Q11, 2026-08-19):
- CLI: `--orgao {MinC,MTur,both}` em measure/report (default `MinC`); novo subcomando `pyauditor consolidate <competencia>`.
- `consolidate` lê só os workbooks por órgão; erro claro se algum faltar; nunca refaz 1.3.
- Input: `data_dir/<órgão>/<AAAA>/<MM>`. Outputs: `roms/<órgão>/<comp>/`, `reports/relatorio_<comp>_<orgao>.xlsx`, consolidado `reports/relatorio_<comp>_consolidado.xlsx`.
- `consolidate` substitui `orgao_consolidation.py` (remover o pooling dentro de `report`).
- Por-ativo (1.4/1.5/1.14) não consolidam — uma linha por órgão por ativo.
- Escopo da planilha consolidada = núcleo financeiro: `CAPA_E_CONTROLE`, `INMS_BASE`, `GLOSAS`, `CALCULO_PAGAMENTO`, `SERVICOS_POR_ORGAO`.
- Cada órgão tem capa própria (`capa_<orgao>.xlsx`).
- Configs por órgão: `configs/<órgão>/inms-*.yaml`.

## Not yet specified

- Dados reais do MTur (fiscalização) — quando chegarem, revalidar 1.2/1.3/2.1 e acceptance (hoje placeholders sintéticos espelham o MinC).
- Rollover de glosa entre competências / aba `HISTORICO` — depende de decisão de escopo futura.
- Fórmula de consolidação por-ativo (1.4/1.5/1.14) — só se o Termo de Referência definir uma fórmula específica; hoje fica por-órgão.

## Out of scope

- Reproduzir as 17 abas da planilha de inspiração — escopo cortado no núcleo financeiro (CHECKLIST_FISCAL, RELATORIO_FISCAL, PAINEL_GERENCIAL, EVIDENCIAS, HISTORICO ficam fora).
- Fórmula de consolidação por-ativo (1.4/1.5/1.14) — decidido manter por-órgão até o TR definir.