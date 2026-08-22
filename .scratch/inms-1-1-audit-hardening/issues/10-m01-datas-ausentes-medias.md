# 10 — M-01: Registros sem datas entram nas médias como zero ou valores inválidos

**Severidade:** Média

**Status:** needs-triage

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

- [ ] Registros com data ausente ou encerramento anterior à abertura são excluídos de `AVERAGE`/`MEDIAN` (não zerados)
- [ ] Contagem de registros rejeitados exposta na planilha
- [ ] Teste: encerramento anterior à abertura não distorce a média/mediana da Seção 8
