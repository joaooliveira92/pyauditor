# 13 — M-04: Tolerância de um minuto está hardcoded e pouco visível

**Severidade:** Média

**Status:** resolved

## Problema

A tolerância de um minuto aparece duplicada em dois lugares conceitualmente
equivalentes (`abc + 1/1440` e `timedelta(hours=2, minutes=1)`). Estão alinhados
hoje, mas não há constante nomeada nem justificativa contratual registrada —
risco de dessincronia em edições futuras.

## Correção recomendada

Se `excel/_datetime.py` for criado para o ticket 02 (C-02), a constante de
tolerância pertence lá — datas/prazos são conceito compartilhável, não exclusivo
do INMS 1.1:

```python
PRAZO_TOLERANCIA_MINUTOS: Final[int] = 1
```

Usar a constante nos dois pontos e documentar se a tolerância decorre de
arredondamento dos dados, granularidade do CSV, regra contratual ou decisão
técnica.

## Critério de aceite

- [x] Constante `PRAZO_TOLERANCIA_MINUTOS` criada em `excel/_datetime.py` e usada nos dois pontos
- [x] Origem/justificativa da tolerância documentada em comentário
- [x] Teste garantindo que os dois pontos permanecem sincronizados (ex.: ambos derivam da mesma constante)

## Answer

Resolvido como parte do ticket 02 (C-02): `PRAZO_TOLERANCIA_MINUTOS: Final[int] = 1`
criada em `excel/_datetime.py` com comentário explicando que é tolerância de
arredondamento de minuto entre origens de dado, não regra contratual. Usada na
fórmula `AC` (`{PRAZO_TOLERANCIA_MINUTOS}/1440`) e no `timedelta(...,
minutes=PRAZO_TOLERANCIA_MINUTOS)` da amostragem da Seção 7 — os dois pontos
agora derivam da mesma constante, eliminando o risco de dessincronia.

Teste: `test_prazo_tolerancia_minutos_used_consistently` em
`tests/test_inms_1_1_audit.py`, verificando que a fórmula `AC2` referencia o
valor de `PRAZO_TOLERANCIA_MINUTOS` importado do módulo compartilhado.
