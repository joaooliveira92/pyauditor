# 05 — A-03: `target_operator == "<="` não é suportado semanticamente de ponta a ponta

**Severidade:** Alta

**Linhas afetadas:** 401–408, 443–450, 868–900.

**Status:** resolved

## Problema

O resumo e parte da penalidade invertem o operador corretamente, mas a memória de
cálculo continua orientada a meta mínima ("Quantidade mínima dentro do prazo p/
atingir a meta:", `=ROUNDUP(B13*A13,0)`) e a Seção 3 fixa "Desvio em pontos
percentuais (Resultado - Meta): =E13-A13". Para uma métrica com meta `<=`, os
conceitos de "quantidade mínima dentro do prazo" e "abaixo do mínimo" deixam de
fazer sentido.

Na Seção 9, o label é sempre "Diferença (Meta - Resultado)" mas a fórmula
`=E13-A13` calcula Resultado - Meta, contradizendo o próprio label.

## Correção recomendada

Escolher uma das duas opções:

1. Restringir este renderer a `target_operator == ">="`, falhando explicitamente
   (`ValueError`) para qualquer outro operador — mais simples e seguro se o
   domínio do INMS 1.1 garante meta mínima.
2. Implementar labels, fórmulas e narrativa específicos para cada direção de meta.

## Critério de aceite

- [x] Decisão registrada (restringir vs. implementar as duas direções)
- [x] Se restringir: `write_sheet()` valida `target_operator` na fronteira e falha com mensagem clara para `<=`
- [ ] ~~Se implementar: labels e fórmulas da Seção 3 e Seção 9 corrigidos~~ (não aplicável — decisão foi restringir)
- [x] Teste: operador `<=` (ver matriz de testes do spec.md)

## Answer

Opção 1 (restringir): `write_sheet()` agora valida em `_validate_write_sheet_params()`
que `target_operator == ">="`, lançando `ValueError` explícito para qualquer outro
valor (incluindo `"<="`). Motivo da escolha: a Seção 3 (memória de cálculo —
"quantidade mínima dentro do prazo", narrativa da margem) e a Seção 9 (penalidade)
só têm semântica coerente para meta mínima; não há hoje nenhum caso real do INMS
1.1 com meta-teto (`<=`) — o próprio nome do indicador ("Incidentes atendidos
dentro do prazo") só faz sentido como piso contratual. Implementar as duas
direções manteria código morto/nunca exercitado em produção e dobraria a
superfície de teste de todas as fórmulas de texto condicional.

Como consequência, os ramos `else` (`target_operator == "<="`) das Seções 2, 7 e 9
foram removidos (eram simétricos e nunca mais alcançáveis) — `target_operator`
deixou de ser passado para `_write_section_2_resumo`, `_write_section_7_auditoria`
e `_write_section_9_penalidade`.

`sintetico.py` captura o `ValueError` na chamada de `inms_1_1_audit.write_sheet()`
e degrada para o renderer genérico (`_write_grupo_executor_sheet`), como as
demais falhas por-INMS do loop — um contrato com `target_operator: "<="`
configurado não derruba o workbook inteiro, só perde a aba enriquecida.

Teste: `test_target_operator_le_is_rejected` em `tests/test_inms_1_1_audit.py`.
