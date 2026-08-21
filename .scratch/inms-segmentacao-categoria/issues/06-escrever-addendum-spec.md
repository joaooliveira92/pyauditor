# 06 — Escrever addendum ao spec.md

Type: task
Status: resolved

Blocked by: 02, 03, 04, 05

## Question

Consolidar as decisões dos tickets 01–05 numa nova seção de `docs/spec/inms-pipeline.md` (ou um documento anexo referenciado por ele) descrevendo: o modelo Categoria/Grupo executor, o mapeamento declarativo completo, a etapa `split`, o xlsx sintético, e como isso compõe com o fog multi-asset/ingestão manual já documentado. Este é o destino do mapa — implementação real fica para tickets de execução separados (mesmo padrão de `.scratch/inms-pipeline/issues/`).

## Answer

Consolidado como novo `## 14. Segmentação por Categoria/Grupo executor` em
`docs/spec/inms-pipeline.md` (5 subseções: 14.1 modelo, 14.2 mapeamento declarativo, 14.3 etapa
`split`, 14.4 xlsx sintético, 14.5 composição com multi-ativo), com um `Fog remanescente deste
addendum` cobrindo os dois itens que ficaram em "Not yet specified" no mapa (revisão periódica de
`categorias.yaml`; texto exato do log do CLI para "não ativado"). Nenhuma decisão dos tickets 01–05
foi alterada — só transcrita e organizada em prosa de spec, com referências cruzadas às seções
existentes (§2.2, §11.3 para 1.8/1.10; ADR 0002; item multi-ativo na lista de fog resolvido).

Este é o destino do mapa — nenhum ticket novo é gerado. A implementação real (código) fica para
tickets de execução separados, mesmo padrão de `.scratch/inms-pipeline/issues/`.
