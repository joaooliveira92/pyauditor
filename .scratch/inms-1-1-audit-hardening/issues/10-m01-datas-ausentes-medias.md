# 10 — M-01: Registros sem datas entram nas médias como zero ou valores inválidos

**Severidade:** Média

**Status:** resolved

## Problema

A coluna `_AG` (`={wc}-{uc}`) alimenta `AVERAGE(...)`/`MEDIAN(...)` na Seção 8.
Além das datas ausentes (ver ticket 02 — C-02), não há verificação de
encerramento anterior à abertura: durações negativas podem entrar na média e na
mediana.

## Correção recomendada

Retornar vazio quando os dados forem incompletos ou cronologicamente inválidos
(encerramento < abertura), e contar separadamente os registros rejeitados, em
vez de deixá-los contaminar `AVERAGE`/`MEDIAN`.

## Critério de aceite

- [x] Registros com data ausente ou encerramento anterior à abertura são excluídos de `AVERAGE`/`MEDIAN` (não zerados)
- [x] Contagem de registros rejeitados exposta na planilha
- [x] Teste: encerramento anterior à abertura não distorce a média/mediana da Seção 8

## Answer

A exclusão de `AVERAGE`/`MEDIAN` já existia parcialmente antes deste ticket: a
fórmula `_AG` (`=IF(OR(U="",W="",W<U),"",W-U)`) já devolvia `""` (texto,
ignorado por `AVERAGE`/`MEDIAN`) tanto para datas ausentes/malformadas quanto
para encerramento anterior à abertura — herdado do trabalho do ticket 02
(C-02)/03 (A-01). O que faltava, e foi adicionado agora, é a contagem exposta
de registros rejeitados: a Seção 8 ganhou uma linha "Registros excluídos da
média/mediana (data ausente/inválida ou encerramento antes da abertura):" com
`=COUNTIF($AG$2:$AG$N,"")`, para que a média/mediana acima não pareça cobrir
100% dos incidentes sem dizer quantos foram excluídos.

Teste: `test_section_8_exposes_rejected_record_count` em
`tests/test_inms_1_1_audit.py`, usando a mesma fixture de datas inválidas do
ticket 02 (uma linha com data de abertura malformada, uma com encerramento
vazio, uma válida) e verificando a fórmula da contagem.
