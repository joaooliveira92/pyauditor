# 11 — M-02: Atraso médio usa a classificação do fornecedor, não o atraso calculado

**Severidade:** Média

**Linhas afetadas:** 839–840.

**Status:** needs-triage

## Problema

`=AVERAGEIF(X, "N", AF)` seleciona pela coluna "No prazo (fornecedor)", mas o
atraso médio é calculado contra o limite ITSM. Pode haver divergência: fornecedor
marcou "N" mas `DataHoraFim <= DataHoraLimite`, ou marcou "S" mas o cálculo indica
atraso — a divergência não fica refletida na média.

## Correção recomendada

Nomear claramente a métrica como "atraso médio dos registros marcados pelo
fornecedor como fora do prazo" (se essa for a intenção), ou trocar o critério de
seleção para a coluna calculada (`_AD`), consistente com o rótulo "atraso médio".

## Critério de aceite

- [ ] Decisão registrada: renomear label ou trocar critério de seleção para `_AD`
- [ ] Fórmula/label atualizados de forma consistente
- [ ] Teste: caso com divergência entre classificação do fornecedor e cálculo ITSM cobre o comportamento escolhido
