Type: grilling
Status: resolved
Blocked by: 01

## Question

Com o detalhe financeiro da planilha de inspiração documentado (ticket [Mapear as abas financeiras da planilha de inspiração](01-inspiration-financial-tabs.md)), decidir a **fórmula da consolidação (2.1)** para o `consolidate`:

- Como `GLOSAS` dos dois órgãos se fundem: soma direta das penalidades por indicador? Uma linha por indicador por órgão + linha consolidada?
- Como `CALCULO_PAGAMENTO` combina os dois órgãos: valor-base somado? Percentual de ajuste recombinado? Glosa total = soma das glosas por órgão?
- O que a linha consolidada de `INMS_BASE` usa: pooled (Σnum/Σden), penalidade = soma das penalidades por órgão, conforms por meta (regra já existente em `excel/orgao_consolidation.py`)?
- Confirma que `consolidate` **substitui** o pooling dentro de `report` (`orgao_consolidation.py`), resolvendo o ticket 07 do framework-audit.

## Answer

Fórmula da consolidação decidida em grilling (rondas 1–2, 19/08/2026):

**`GLOSAS` (estrutura)**
- Uma linha por **(indicador × órgão)** (Resultado/Meta/Faixa/%Ajuste/Valor Base/Valor Glosa) + resumo (Total de Pontos, Limite, Percentual Aplicado, Valor da Glosa), como a inspiração.
- Teto único sobre o agregado dos dois órgãos (30% do valor mensal), não por órgão.
- `%Ajuste` por linha derivado da engine: `(déficit/passo) × pontos-por-passo × 0.001`, exceto INMS 1.2 (regra manual; config por órgão, ticket 03). `Valor Glosa` linha = `Valor Base × %Ajuste/100`.

**Fonte dos pontos e automazione da cadeia**
- Total de Pontos = Σ(%Ajuste × 1000) sobre todas as linhas MinC+MTur; **derivado**, eliminando a entrada manual ("D14") da planilha de inspiração. O 2.1 automatiza a cadeia indicador→pontos→glosa no agregado; teto 30% aplicado uma única vez sobre o agregado.

**`CALCULO_PAGAMENTO`**
- Espelha a inspiração: colunas MinC/MTur/Consolidado; rateio fiscal como parámetro (default provisório 0.5/0.5), `Valor bruto = mensal × rateio`; glosa na coluna consolidada `=MIN(pontos×0.001, teto) × bruto`; `Valor recomendado = MAX(0, bruto−glosa−outros)`.
- Rateio e limite de glosa viram parâmetros fiscais (config), não mais espiritual.

**`INMS_BASE` consolidada**
- Mantém a regra atual, sem alteração semântica: pooling `Σnum/Σden`, `conforms` pela meta consolidada, `penalty = soma das penalties por órgão`, sem reaplicar a fórmula de degrau; por-ativo 1.4/1.5/1.14 seguem sem consolidar. O pooling **sai** do `report` e passa a viver no `consolidate` (resolve o ticket 07 do framework-audit).

**Sugestão de glosa (decisão nova, aprovada Q7–Q10)**
- O `consolidate` produz **sugestão de glosa**: linhas com `%Ajuste`/`Valor Glosa` sugeridos e colunas de decisão vagas (`Justificativa`, `Decisão Fiscal`, `Observação`), como a inspiração.
- O fiscal revisa e **aceita** (ou não) a justificativa do fornecedor: aceitar = **anistia/bn** (a ocorrência sai da base, `%Ajuste` zera); não aceitar = glosa mantida. A glosa de competência = só sobre as ocorrências não-anistadas.
- Decisões vivem na própria planilha consolidada (colunas de decisão), não em arquivo paralelo.
- **Re-rodada do `consolidate`** sobre planilha já decorada: merge — reconstrói/recalcula linhas novas mas **preserva** decisões/justificativas preenchidas (nunca sobrescreve células editadas).
- `Reincidência`: coluna existe mas não altera o cálculo no 2.1 (histórico fora do escopo/patch HISTORICO).