# 01 - Representação da glosa não calculada

Type: grilling
Status: resolved

## Question

Como o pipeline deve representar uma glosa monetária **não calculada** — quando `Valor mensal vigente` está ausente na capa — em cada superfície de saída, sem que ela possa ser confundida com uma glosa legítima de `0.00`?

Hoje `excel/consolidate.py` (build_glosas e build_calculo) e `cli/consolidate.py` escrevem/logam `0.00` quando `valor_base is None` (glosa_final = 0.0), e `cli/report.py` já loga o aviso de capa sem valor mensal. A revisão pede: separar `%Ajuste` de valor monetário e de status do cálculo; nunca preencher célula numérica com zero; marcar relatórios incompletos como rascunho.

Decisões em aberto:
- Qual o vocabulário do status? (`não calculada`, `indisponível`, `pendente` — e o motivo).
- Como fica cada célula Excel do GLOSAS/CALCULO_PAGAMENTO quando não calculada (vazia + célula de status? texto? formato)?
- `%Ajuste` (percentual) continua sendo calculado mesmo sem valor mensal? (exigido pela própria regra do TR §12.)
- O `0.00` legítimo (valor presente, pontos zerados) permanece numericamente zero — o que o distingue do não calculado?
- Onde o status aparece no resumo final e nos logs?

Contexto: review.md §1 (alta prioridade), §"Perguntas que eu levaria para a equipe" (regras de negócio), cenário de teste "glosa calculável / não calculável / garantia de que não calculada nunca vire zero".

## Answer

Desabilitado por grilling (HITL), com base no TR (item 35 / fórmula): **`Ajuste_NMS = min(30%, Σ Pontos_NMS × 0,001%)`**, e `Pagamento_mensal = PM_item × (1 − Ajuste_NMS)` — o percentual não depende do valor mensal.

1. **Vocabulário**: **`não calculada`** (fato), com `motivo=valor mensal ausente` como dado secundário. Excluídos `indisponível` (sugere falha técnica) e `pendente` (sugere resolução futura).
2. **Células Excel**: células monetárias **vazias** em GLOSAS e CALCULO_PAGAMENTO (nunca `0.00`, nunca texto) + **célula de status** `não calculada`. Nunca preencher célula numérica com zero.
3. **`%Ajuste`**: **sempre calculado** mesmo sem valor mensal — dimensão independente do valor (confirmado pelo TR §12/35).
4. **Distinção `0.00`**: o status distingue; `0.00` legítimo (PM presente, pontos zerados → glosa real zero) permanece numérico; `não calculada` não é número. O TR respalda: 0.00 = resultado de "0% aplicado"; ausência de PM não é resultado.
5. **Superfícies**: a célula (item 2), o log `cli/consolidate.py:128` (trocar `glosa: 0.00` por `glosa: não calculada`), e o resumo final (ticket 04 herda). Código de saída é do ticket 03.

**Nova fonte de dados (dada pelo usuário nesta sessão)**: abandono de `capa.xlsx`/`capa_MinC.xlsx`/`capa_MTur.xlsx`; passar a usar `objetos.csv`, `capa.csv`, `capa_MinC.csv`, `capa_MTur.csv`. `objetos.csv` (R$ mensal por item contratual, total R$ 461.063,58/mês) passa a ser a fonte do valor monetário; capas individuais perdem `Valor mensal vigente`/`Valor global anual`; comuns (contrato, SEI, empresa, vigência, etc.) vão só para `capa.csv`. Registrado em ticket novo (migração das capas para CSV).