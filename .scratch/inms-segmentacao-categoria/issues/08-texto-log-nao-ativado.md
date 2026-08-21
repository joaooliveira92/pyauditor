# 08 — Texto exato do log do CLI para "não ativado"

Type: grilling
Status: resolved

Blocked by: 01, 04

## Question

O ticket 04 fixou a frase do xlsx sintético para INMS "não ativado" (dataset ausente na
competência): `"Esse serviço não foi requisitado no período selecionado."`. O ticket 01 (item 16)
exigiu que essa ausência também fique explícita no log do CLI, mas não formalizou o texto exato nem
se é a mesma frase ou uma variante, nem em qual comando (`split` ou `measure`) ela é emitida.

## Answer

Resolvido via grilling (2 perguntas, ambas aprovadas).

1. **Forma: telegráfica/estruturada no log, não a frase em prosa do xlsx.** Públicos diferentes —
   operador lendo o terminal vs. leitor do relatório final. Texto exato:

   ```
   WARNING: INMS 1.8 (MinC/2026-06): não ativado — dataset ausente (serviço não requisitado no período)
   ```

   Formato: nível `WARNING` (não `ERROR` — não é falha, ticket 01 item 15), INMS + órgão + competência
   entre parênteses (mesmos três eixos usados nos demais logs de `measure`/`split`), motivo curto ao
   final.

2. **Ponto de emissão: só `measure`, não duplicado em `split`.** `measure` é quem efetivamente
   descobre a ausência do dataset (regra geral do engine, ticket 01 item 15) — `split` nem processa
   INMS em `whole_indicator` nem é o ponto de descoberta para o caso geral. Logar só onde a ausência
   é descoberta evita ruído duplicado quando `run` executa os dois comandos em sequência.
