# 11 — M-02: Atraso médio usa a classificação do fornecedor, não o atraso calculado

**Severidade:** Média

**Linhas afetadas:** 839–840.

**Status:** resolved

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

- [x] Decisão registrada: renomear label ou trocar critério de seleção para `_AD`
- [x] Fórmula/label atualizados de forma consistente
- [x] Teste: caso com divergência entre classificação do fornecedor e cálculo ITSM cobre o comportamento escolhido

## Answer

Decisão: trocar o critério de seleção para a coluna calculada `_AD` ("No prazo
— data limite ITSM"), não renomear o label. O label já diz "vs. limite ITSM";
selecionar por `_X` ("No prazo (fornecedor)") contradizia o próprio label — a
fórmula agora é `=IF(COUNTIF($AD$2:$AD$N,"N")=0,"Sem atrasos",AVERAGEIF($AD$2:$AD$N,"N",$AF$2:$AF$N))`.
De brinde, isso também corrige um `#DIV/0!` que existia mesmo antes deste
ticket (`AVERAGEIF` sem nenhuma correspondência gera erro, e não havia guarda
— um caso de div-por-zero que a auditoria original do ticket 03/A-01 não
cobria porque não depende de `B13`).

Teste: `test_atraso_medio_uses_itsm_calculated_column` em
`tests/test_inms_1_1_audit.py`, verificando que a fórmula referencia `$AD$2:$AD$5`
e não `$X$2:$X$5`, e que tem a guarda `"Sem atrasos"`.
